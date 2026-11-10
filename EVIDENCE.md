# Studionet evidence

- Network: Studionet (61999)
- [Contract address](https://explorer-studio.genlayer.com/address/0xaa9b710d83B34Bb01dD47234B1f8cBf85B8370ba)
- [Deployment](https://explorer-studio.genlayer.com/tx/0x599aba6f4058832250c96f7f2ac1a49b87ca87a5101781f1d3355f7eb55ca369)
- [Register synthetic recall](https://explorer-studio.genlayer.com/tx/0x80e82d4c764b9fe5e5a23eb802c421205bc03d88c315a76c08fdd4b2e615f84b)
- [Post synthetic notice](https://explorer-studio.genlayer.com/tx/0x889f1a8e5bf9592391f8d286a0dec10bdbeae224fbcea44ff89e8d2144a12d31)
- [Review synthetic obligation](https://explorer-studio.genlayer.com/tx/0x397c98739116efc187ba237c2a1c4d7aa963cbcfeae610173e5c64e555dcb09a)

Explorer showed all four transactions as FINALIZED with successful GenVM execution. The smoke case used recall ID `ab29e39363da10b1e8d262e66ea32b4fc04f2e220ed5220d0cc54662e07823a5`, recipient `0x2222222222222222222222222222222222222222`, and batch `LOT-001`. Studio read back the notice with no recipient response. The expected aggregate verdict is INCONCLUSIVE. The aggregate finalization write was not submitted. This smoke case exercises the dispatch-without-acknowledgment path. The model-assisted acknowledgment and denial paths were tested locally with mocked model outputs.

## Local verification

`python -m unittest discover -s tests -v` passed 10 tests covering all four verdicts, sender authorization, evidence hash binding, deadlines, immutable decisions, missing evidence and ungrounded model output.
