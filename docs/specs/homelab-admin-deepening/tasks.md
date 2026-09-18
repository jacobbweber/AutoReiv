# Tasks: Homelab Admin Deepening & Multi-Capability Factory Evolution (CARD-357)

- [ ] Task 1: Auto-resolve active project in `FactoryDispatchTools.launch_factory_training` (`src/application/skills/factory_dispatch_tools.py`) [REQ-FACT-070].
- [ ] Task 2: Implement dynamic script-aware tool synthesis and action augmentation in `ToolSynthesizer._synthesize_grounded_project_tool` (`src/application/orchestration/tool_synthesizer.py`) [REQ-FACT-071, REQ-FACT-072].
- [ ] Task 3: Enhance `AuthorPhase` to load and pass existing tool code into the prompt to prevent capability regression (`src/application/agent_training_factory/phases/author.py`) [REQ-FACT-072].
- [ ] Task 4: Enhance `BlueprintPhase` to cleanly formulate companion skills when deepening an existing pack (`src/application/agent_training_factory/phases/blueprint.py`) [REQ-FACT-073].
- [ ] Task 5: Register requirements in `docs/rtm.json` and author unit tests for dispatch tools, dynamic synthesis, and tool augmentation.
- [ ] Task 6: Execute live training job for `homelab-admin` to add direct Hyper-V VM orchestration and switch management (`LabManager.ps1`, `HyperVDriver.psm1`), promote certified pack, and test live execution.
