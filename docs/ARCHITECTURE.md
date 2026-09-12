# OMEGA architecture

OMEGA is a personal assistant platform, not a single autonomous process. The conversational core decides what to say; it does not receive unrestricted device access.

## Planned layers

1. **Interface:** terminal, voice nodes, desktop UI, and mobile UI.
2. **Orchestrator:** conversation, intent routing, context, and approvals.
3. **Intelligence:** interchangeable local or authorized remote language models.
4. **Memory and knowledge:** user-controlled memories, documents, retrieval, and citations.
5. **Integration Hub:** permission-controlled adapters for robots and smart-home systems.
6. **Perception:** explicit microphone and camera sessions, motion events, and object detection.
7. **Audit and safety:** authentication, action logs, rate limits, emergency stop, and network isolation.

## Robot hive

Each robot is a node with its own identifier, capabilities, health state, and emergency stop. OMEGA sends typed tasks through the Integration Hub. Nodes must reject unsupported commands locally. Loss of connectivity must stop motion or place the robot in a safe state. The system will not support weapons.

## Smart home

Smart lights and household devices will be implemented as adapters. Prefer a local home-automation coordinator so device credentials are not copied into every OMEGA component. Consequential actions require confirmation and all actions are logged.

## Voice satellites

Small room devices can act as OMEGA satellites: wake-word detection, microphone, speaker, mute control, and a visible listening indicator. They forward requests to the central OMEGA service and retain minimal data.

## Security and vision

Camera processing will be opt-in, visibly active, and separated from conversational memory. The initial vision pipeline will detect motion and classify objects. Recording, recognition, remote access, and notifications are separate permissions. Face recognition is not assumed and should only be added with explicit consent and applicable legal review.

## Trust rules

- Deny device access by default.
- Never expose credentials to the language model.
- Store secrets outside source control.
- Require confirmation for physical, destructive, costly, or privacy-sensitive actions.
- Treat model output as a proposal, never as authorization.
- Provide a physical and software emergency stop for moving hardware.
- Preserve audit logs without storing unnecessary camera or microphone content.
