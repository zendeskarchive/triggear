package com.futuresimple.triggear

enum EventType {
    LABEL('labeled'),
    PUSH('push'),
    TAG('tagged'),
    PR_OPEN('opened')

    EventType(String eventName) {
        this.eventName = eventName
    }
    private final String eventName

    String getEventName() {
        return eventName
    }
}
