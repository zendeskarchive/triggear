class EventTypes:
    release = 'release'
    comment = 'created'
    synchronize = 'synchronize'
    labeled = 'labeled'
    tagged = 'tagged'
    push = 'push'
    pr_opened = 'opened'
    pull_request = 'pull_request'

    @staticmethod
    def get_allowed_registration_event_types():
        return [EventTypes.labeled,
                EventTypes.tagged,
                EventTypes.pr_opened,
                EventTypes.push,
                EventTypes.release]
