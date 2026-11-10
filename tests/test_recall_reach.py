"""Local contract-logic tests with a minimal GenLayer stand-in."""
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class UserError(Exception):
    pass


def public(method):
    return method


runtime = ModuleType("genlayer")
runtime.TreeMap = dict
runtime.u256 = int
runtime.gl = SimpleNamespace(
    Contract=object, public=SimpleNamespace(write=public, view=public),
    message=SimpleNamespace(sender_address=""), vm=SimpleNamespace(UserError=UserError),
    nondet=SimpleNamespace(exec_prompt=None),
    eq_principle=SimpleNamespace(strict_eq=lambda evaluate: evaluate()),
)
spec = importlib.util.spec_from_file_location(
    "recall_reach", Path(__file__).parents[1] / "contracts" / "recall_reach.py",
)
contract = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"genlayer": runtime}):
    spec.loader.exec_module(contract)

MAKER = "0x" + "11" * 20
SHOP = "0x" + "22" * 20
OTHER = "0x" + "33" * 20
BATCH = "LOT-001"
NOTICE = "Stop sale and quarantine all units in LOT-001."
ACK = "We received the recall notice for LOT-001."
DENIAL = "We missed the recall notification deadline for LOT-001."


class RecallTests(unittest.TestCase):
    def setUp(self):
        self.clock = 100
        self.addCleanup(patch.stopall)
        patch.object(contract.time, "time", lambda: self.clock).start()
        self.ic = contract.RecallReach()
        for name in ("recalls", "notices", "responses", "reviews", "decisions"):
            setattr(self.ic, name, {})
        self.sender(MAKER)
        self.model("RECEIVED", NOTICE, ACK)

    def sender(self, address):
        runtime.gl.message.sender_address = address

    def model(self, status, notice_quote, response_quote):
        runtime.gl.nondet.exec_prompt = lambda *a, **k: {
            "status": status, "notice_quote": notice_quote, "response_quote": response_quote,
        }

    def register(self, recipients=(SHOP,)):
        return self.ic.register_recall(
            "sample", "Stop sale and quarantine", json.dumps([[r, BATCH] for r in recipients]), 10, 20,
        )

    def notice(self, recall_id):
        self.sender(MAKER)
        return self.ic.post_notice(recall_id, SHOP, BATCH, NOTICE)

    def acknowledge(self, recall_id, notice_hash):
        self.sender(SHOP)
        return self.ic.respond(recall_id, BATCH, notice_hash, "RECEIVED", ACK)

    def finish(self, recall_id, recipients=(SHOP,)):
        self.clock = 121
        for recipient in recipients:
            self.ic.review(recall_id, recipient, BATCH)
        receipt = json.loads(self.ic.finalize(recall_id))
        self.assertEqual(contract.digest(receipt["decision"]), receipt["decision_hash"])
        return receipt["decision"]

    def test_timely_receipt_and_immutable_decision(self):
        recall_id = self.register()
        notice_hash = self.notice(recall_id)
        self.clock = 110
        self.acknowledge(recall_id, notice_hash)
        self.assertEqual(self.finish(recall_id)["outcome"], "VERIFIED")
        with self.assertRaisesRegex(UserError, "already finalized"):
            self.ic.finalize(recall_id)

    def test_dispatch_is_inconclusive(self):
        recall_id = self.register()
        self.notice(recall_id)
        self.assertEqual(self.finish(recall_id)["outcome"], "INCONCLUSIVE")

    def test_partial_coverage(self):
        recall_id = self.register((SHOP, OTHER))
        self.acknowledge(recall_id, self.notice(recall_id))
        decision = self.finish(recall_id, (SHOP, OTHER))
        self.assertEqual(decision["outcome"], "PARTIAL")
        self.assertEqual(decision["counts"], {"RECEIVED": 1, "MISSED": 0, "UNKNOWN": 1})

    def test_late_notice(self):
        recall_id = self.register()
        self.clock = 111
        self.notice(recall_id)
        self.assertEqual(self.finish(recall_id)["outcome"], "VIOLATION")

    def test_late_ack_is_inconclusive(self):
        recall_id = self.register()
        notice_hash = self.notice(recall_id)
        self.clock = 111
        self.acknowledge(recall_id, notice_hash)
        self.assertEqual(self.finish(recall_id)["outcome"], "INCONCLUSIVE")

    def test_grounded_recipient_denial(self):
        recall_id = self.register()
        self.sender(SHOP)
        self.clock = 111
        self.ic.respond(recall_id, BATCH, "", "MISSED", DENIAL)
        self.model("MISSED", "", DENIAL)
        self.assertEqual(self.finish(recall_id)["outcome"], "VIOLATION")

    def test_hallucinated_quote_is_inconclusive(self):
        recall_id = self.register()
        self.acknowledge(recall_id, self.notice(recall_id))
        self.model("RECEIVED", NOTICE, "Fabricated proof of receipt.")
        self.assertEqual(self.finish(recall_id)["outcome"], "INCONCLUSIVE")

    def test_authorization_binding_and_duplicates(self):
        recall_id = self.register()
        self.sender(OTHER)
        with self.assertRaisesRegex(UserError, "manufacturer only"):
            self.ic.post_notice(recall_id, SHOP, BATCH, NOTICE)
        notice_hash = self.notice(recall_id)
        with self.assertRaisesRegex(UserError, "already recorded"):
            self.notice(recall_id)
        with self.assertRaisesRegex(UserError, "unknown obligation"):
            self.ic.respond(recall_id, BATCH, notice_hash, "RECEIVED", ACK)
        with self.assertRaisesRegex(UserError, "hash mismatch"):
            self.acknowledge(recall_id, "0" * 64)

    def test_registration_rejects_self_and_duplicates(self):
        with self.assertRaisesRegex(UserError, "self-acknowledgment"):
            self.register((MAKER,))
        with self.assertRaisesRegex(UserError, "duplicate obligation"):
            self.register((SHOP, SHOP))
        self.register()
        with self.assertRaisesRegex(UserError, "already exists"):
            self.register()

    def test_review_timeout_is_fail_closed(self):
        recall_id = self.register()
        with self.assertRaisesRegex(UserError, "evidence still open"):
            self.ic.review(recall_id, SHOP, BATCH)
        self.clock = 121
        with self.assertRaisesRegex(UserError, "review outstanding"):
            self.ic.finalize(recall_id)
        self.clock += 86400
        self.assertEqual(json.loads(self.ic.finalize(recall_id))["decision"]["outcome"], "INCONCLUSIVE")
        with self.assertRaisesRegex(UserError, "already finalized"):
            self.ic.review(recall_id, SHOP, BATCH)
