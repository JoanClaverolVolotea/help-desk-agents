# Help Desk Agent Demo

This folder contains a root-level multi-agent IT help desk demo focused on two ticket types:

1. `USDV-176285`: eCrew login/access reset.
2. `USDV-176893`: New employee onboarding for E-MAIL/EFOS/PELESYS.

The flow is:

1. Triage agent reads free-text ticket input.
2. Triage uses `lookup_case_tool` to detect known case metadata.
3. Triage hands off to:
   - Access Reset Specialist, or
   - Onboarding Specialist.
4. Specialist runs deterministic local mock tools and returns a bilingual response (English + Espanol).

## Files

- `models.py`: Case category and case data model.
- `case_catalog.py`: Known ticket catalog and detection logic.
- `tools.py`: Deterministic local mock tools.
- `help_desk_agents.py`: Triage and specialist agent configuration.
- `main.py`: Interactive CLI runner.

## Run

From repo root:

```bash
uv run python help-desk-agent/main.py
```

Then paste ticket text. You can exit with `exit` or `quit`.

## Sample input: Access reset

```text
Reset de acceso Ecrew:
https://volotea.atlassian.net/browse/USDV-176285 - Francois Emeriau- Log in problem into eCrew
Tipo de actividad: Service request
Portal Group: Login ans accounts
Tipo de sol: Fix an account issue
```

## Sample input: Onboarding

```text
https://volotea.atlassian.net/browse/USDV-176893 - ALTAS E-MAIL/EFOS/PELESYS 16-02-2026
Tipo de actividad: Service request
Portal group: Login ans accounts
Tipo de sol: Onboard new employee
```
