# Agent Telemetry SDK v2

`agent_v2` is the stable backend-compatible SDK version in the LogarithmixAI telemetry SDK line. This version is especially important because its event types and payload structure align with the backend telemetry pipeline design used in the project.

## Version Purpose

- Stable backend-compatible telemetry SDK
- Reference version for telemetry pipeline integration
- Clean source-form SDK preserved for compatibility, validation, and future recovery work

## Core Capabilities

- Structured telemetry event generation
- Multi-framework request monitoring for Flask, FastAPI, and Django
- Outgoing HTTP monitoring
- SQLAlchemy database monitoring
- Logging and exception capture
- Function performance monitoring
- Span event generation
- HMAC-secured event transport

## Why This Version Matters

This version serves as the strongest compatibility bridge between the Python SDK and the backend telemetry pipeline. It is the preserved reference point for event routing, event-type mapping, and module-level telemetry processing.

## Installation Direction

This folder represents the `v2.0.0` source package definition. In a versioned distribution model, users should install a released package version rather than manually copying source folders.

## Ownership

- Organization: [LogarithmixAI](https://github.com/LogarithmixAI)
- Author: `ShubhamCoder-In`
- Collaboration model: created and evolved as a collaborative LogarithmixAI SDK effort

## Notes

- `agent_v2` is the preserved backend-compatible SDK line.
- This version is suitable as a reference baseline for compatibility-focused work.
- Newer versions may evolve architecture, but this version remains important for stable backend alignment.
