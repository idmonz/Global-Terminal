# GOAL 12A Quant Model Lab Architecture

## Purpose

The Quant Model Lab adds local model snapshot infrastructure without executing heavy runtimes.

## Modules

- `quant_model_snapshot_schema.py`: model category validation and snapshot dataclass.
- `quant_model_registry.py`: implemented and roadmap model entries.
- `quant_model_lab.py`: deterministic diagnostics and snapshot creation.
- `quant_model_attachment_bridge.py`: Strategy-as-Git artifact attachment.
- `quant_model_report_generator.py`: Report Inbox attachment.

## Categories

- correlation_structure
- volatility_model
- regime_model
- mean_reversion_model
- cointegration_model
- factor_model
- option_model
- foundation_model_placeholder
- rl_simulation_placeholder

## External mapping

- quant-traderr-lab: roadmap for HRP/RMT/GARCH/Kalman/Cointegration/Hurst/OU ideas.
- Kronos: future foundation model snapshot placeholder only.
- tensortrade: future action-less simulation architecture placeholder only.
- QuantDinger: strategy lifecycle and monitoring concept only.

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.
