"""Business rules – Person 3.

Each rule is a function that accepts a Grievance and a db Session and
optionally calls `create_warning_event`.  Register new rules here and
invoke them from engine.py.

Example skeleton:

    def rule_awaiting_response_window(db, grievance):
        ...
        create_warning_event(db, grievance, WarningType.POTENTIAL_DELAY,
                             rule_id="AWAITING_RESPONSE_WINDOW", reason="...")
"""
