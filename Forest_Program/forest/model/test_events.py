import pytest

from forest.model import EventEmitter, ModelEvent


def testMultipleViewsCanSubscribeToSameEventInRegistrationOrder() -> None:
    events = EventEmitter[ModelEvent]()
    calls: list[str] = []
    events.subscribe(ModelEvent.NODES_CHANGED, lambda: calls.append("first-view"))
    events.subscribe(ModelEvent.NODES_CHANGED, lambda: calls.append("second-view"))

    events.notify(ModelEvent.NODES_CHANGED)

    assert calls == ["first-view", "second-view"]


def testCallbacksAreSeparatedByEvent() -> None:
    events = EventEmitter[ModelEvent]()
    calls: list[str] = []
    events.subscribe(ModelEvent.NODES_CHANGED, lambda: calls.append("nodes"))
    events.subscribe(ModelEvent.LAYOUT_CHANGED, lambda: calls.append("layout"))

    events.notify(ModelEvent.LAYOUT_CHANGED)

    assert calls == ["layout"]


def testDuplicateCallbackIsRegisteredOnce() -> None:
    events = EventEmitter[ModelEvent]()
    calls: list[str] = []

    def callback() -> None:
        calls.append("called")

    events.subscribe(ModelEvent.NODES_CHANGED, callback)
    events.subscribe(ModelEvent.NODES_CHANGED, callback)
    events.notify(ModelEvent.NODES_CHANGED)

    assert calls == ["called"]


def testSubscriptionAddedDuringNotificationRunsNextTime() -> None:
    events = EventEmitter[ModelEvent]()
    calls: list[str] = []

    def lateCallback() -> None:
        calls.append("late")

    def firstCallback() -> None:
        calls.append("first")
        events.subscribe(ModelEvent.NODES_CHANGED, lateCallback)

    events.subscribe(ModelEvent.NODES_CHANGED, firstCallback)
    events.notify(ModelEvent.NODES_CHANGED)
    assert calls == ["first"]

    events.notify(ModelEvent.NODES_CHANGED)
    assert calls == ["first", "first", "late"]


def testSubscribeRejectsNonCallable() -> None:
    events = EventEmitter[ModelEvent]()
    with pytest.raises(TypeError):
        events.subscribe(ModelEvent.NODES_CHANGED, None)  # ty: ignore[invalid-argument-type]


def testCallbackFailureStopsNotificationAndIsPropagated() -> None:
    events = EventEmitter[ModelEvent]()
    calls: list[str] = []

    def failingCallback() -> None:
        raise RuntimeError("view failed")

    events.subscribe(ModelEvent.NODES_CHANGED, failingCallback)
    events.subscribe(ModelEvent.NODES_CHANGED, lambda: calls.append("later"))

    with pytest.raises(RuntimeError, match="view failed"):
        events.notify(ModelEvent.NODES_CHANGED)

    assert calls == []
