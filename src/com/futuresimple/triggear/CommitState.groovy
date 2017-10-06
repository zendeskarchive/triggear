package com.futuresimple.triggear

enum CommitState {
    SUCCESS('success'),
    FAILURE('failure'),
    ERROR('error'),
    PENDING('pending')

    CommitState(String gitHubStateName) {
        this.gitHubStateName = gitHubStateName
    }
    private String gitHubStateName

    String getGitHubStateName() {
        return gitHubStateName
    }
}
