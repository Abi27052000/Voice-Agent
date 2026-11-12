"""Vapi payload builders wire resources together by ID; check the wiring offline."""

from app.agents import call_outcome, dispatcher, handoff, receptionist, squad, tools

IDS = {
    "credential": {"webhook": "cred-1"},
    "tool": {
        tools.CHECK_AVAILABILITY: "tool-avail",
        tools.BOOK_APPOINTMENT: "tool-book",
        tools.CREATE_LEAD: "tool-lead",
        handoff.TO_DISPATCHER: "tool-handoff",
    },
    "structured-output": {call_outcome.KEY: "so-1"},
    "assistant": {receptionist.KEY: "asst-rec", dispatcher.KEY: "asst-disp"},
}


def test_receptionist_can_book_and_hand_off():
    payload = receptionist.build(IDS)
    assert payload["model"]["toolIds"] == ["tool-avail", "tool-book", "tool-lead", "tool-handoff"]
    assert payload["artifactPlan"]["structuredOutputIds"] == ["so-1"]
    assert "assistant.started" in payload["clientMessages"]


def test_dispatcher_only_logs_emergencies():
    payload = dispatcher.build(IDS)
    assert payload["model"]["toolIds"] == ["tool-lead"]  # no booking tools
    assert payload["voice"]["voiceId"] != receptionist.build(IDS)["voice"]["voiceId"]
    assert payload["firstMessageMode"] == "assistant-speaks-first-with-model-generated-message"
    assert payload["server"]["credentialId"] == "cred-1"


def test_handoff_targets_dispatcher_with_context():
    tool = handoff.build_to_dispatcher(IDS)
    dest = tool["destinations"][0]
    assert tool["type"] == "handoff" and dest["assistantName"] == dispatcher.NAME
    assert dest["contextEngineeringPlan"] == {"type": "userAndAssistantMessages"}


def test_handoff_argument_cannot_be_mistyped():
    # Regression: the model once mistyped a UUID destination -> assistant-not-found.
    fn = handoff.build_to_dispatcher(IDS)["function"]
    assert fn["strict"] is True
    assert fn["parameters"]["properties"]["destination"]["enum"] == [dispatcher.NAME]
    assert fn["parameters"]["additionalProperties"] is False


def test_squad_starts_with_receptionist():
    members = squad.build(IDS)["members"]
    assert [m["assistantId"] for m in members] == ["asst-rec", "asst-disp"]
