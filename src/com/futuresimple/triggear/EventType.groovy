package com.futuresimple.triggear

enum EventType {
    LABEL('labeled'),
    PUSH('push'),
    TAG('tagged')

    EventType(String eventName) {
        this.eventName = eventName
    }
    private final String eventName

    String getEventName() {
        return eventName
    }
}
