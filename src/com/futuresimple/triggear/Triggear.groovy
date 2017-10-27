package com.futuresimple.triggear

import groovy.json.JsonOutput

class Triggear implements Serializable {
    private String repository
    private Object context

    /**
     * Create a Triggear object for specific repository
     *
     * @param repositoryFullName full name of GitHub repository, e.g. "futuresimple/triggear"
     */
    Triggear(context, String repositoryFullName) {
        this.context = context
        this.repository = repositoryFullName
    }

    /**
     * Register for PR opened events in repository. If anyone opens new PR, Triggear will trigger this job and try to
     * assign 'triggear-pr-sync' label to PR. If such label does not exist, trigger for sync events won't work.
     *
     * @param requestedParams Parameters that your job will be run with
     */
    void registerForPrOpened(List<RequestParam> requestedParams){
        raiseIfTagRequested(requestedParams)
        register(EventType.PR_OPEN,
            [],
            requestedParams
        )
    }

    /**
     * Register for pushes in repository. If anyone pushes anything to repo this pipeline will be triggered.
     *
     * @param requestedParams Parameters that your job will be run with
     * @param branchRestrictions Branches for which this job should be triggered. Pushes to other branches will be
     * ignored
     */
    void registerForPushes(List<RequestParam> requestedParams,
            List<String> branchRestrictions = [],
            List<String> changeRestrictions = []) {
        raiseIfTagRequested(requestedParams)
        register(EventType.PUSH,
            [],
            requestedParams,
            branchRestrictions,
            changeRestrictions
        )
    }

    /**
     * Register for tags in repository. If anyone pushes a tag into repo this pipeline will be triggered.
     *
     * @param requestedParams Parameters that your job will be run with
     * @param branchRestrictions Branches for which this job should be triggered. Pushes to other branches will be ignored
     */
    void registerForTags(List<RequestParam> requestedParams, List<String> branchRestrictions = []) {
        register(EventType.TAG,
            [],
            requestedParams,
            branchRestrictions
        )
    }

    /**
     * Register for PR labels in repository. If anyone adds such label to PR in repo this pipeline will be triggered.
     *
     * @param label Triggering label name
     * @param requestedParams Parameters that your job will be run with
     */
    void registerForLabel(String label,
                          List<RequestParam> requestedParams) {
        registerForLabels([label], requestedParams)
    }

    /**
     * Register for multiple PR labels in repository. If anyone adds any of that labels to PR in repo this pipeline
     * will be triggered.
     *
     * @param labels Triggering labels names
     * @param requestedParams Parameters that your job will be run with
     */
    void registerForLabels(List<String> labels,
                           List<RequestParam> requestedParams) {
        raiseIfTagRequested(requestedParams)
        register(EventType.LABEL,
            labels,
            requestedParams
        )
    }

    /**
     * Add a GitHub status to commit identified by SHA
     *
     * @param sha SHA of the commit to add status to
     * @param state State that should be shown on comment
     * @param description Short description of status
     * @param statusName Name of status to add. JOB_NAME taken by default
     * @param statusUrl URL that this status should direct to. Current BUILD_URL by default
     */
    void addCommitStatus(String sha,
                         CommitState state,
                         String description,
                         String statusName = '',
                         String statusUrl = '') {
        statusName = statusName != '' ? statusName : context.env.JOB_NAME
        statusUrl = statusUrl != '' ? statusUrl : context.env.BUILD_URL
        sendRequestToTriggearService('status',
            [
                sha        : sha,
                repository : repository.repositoryFullName,
                state      : state.getGitHubStateName(),
                description: description,
                url        : statusUrl,
                context    : statusName
            ]
        )
    }

    /**
     * Add a GitHub comment to commit identified by SHA
     *
     * @param sha SHA of the commit to add comment to
     * @param body Comment content
     */
    void addComment(String sha,
                    String body){
        sendRequestToTriggearService('comment',
        [
            sha: sha,
            repository: repository,
            jobName: context.env.JOB_NAME,
            body: body
        ])
    }

    private void register(EventType eventType,
                          List<String> labels,
                          List<RequestParam> requestedParams,
                          List<String> branchRestrictions = [],
                          List<String> changeRestrictions = []) {
        sendRequestToTriggearService('register',
            [
                eventType           : eventType.getEventName(),
                repository          : repository.repositoryFullName,
                jobName             : context.env.JOB_NAME,
                labels              : labels,
                requested_params    : requestedParams.collect { it.getRequestParam() },
                branch_restrictions : branchRestrictions,
                changeRestrictions  : changeRestrictions
            ]
        )
    }

    private void sendRequestToTriggearService(String methodName, Map<String, Object> payload){
        try {
            context.withCredentials([context.string(credentialsId: 'triggear_token', variable: 'triggear_token')]) {
                URLConnection post = new URL("$context.env.TRIGGEAR_URL" + "${methodName}").openConnection()
                String payloadAsString = JsonOutput.toJson(payload)
                context.println("${methodName} call to Triggear service (payload: " + payload + ")")
                post.setRequestMethod("POST")
                post.setDoOutput(true)
                post.setRequestProperty("Content-Type", "application/json")
                post.setRequestProperty("Authorization", "Token ${context.triggear_token}")
                post.getOutputStream().write(payloadAsString.getBytes("UTF-8"))
                int postResponseCode = post.getResponseCode()
                if (postResponseCode == 200) {
                    context.println(post.getInputStream().getText())
                } else {
                    context.println("Calling Triggears ${methodName} failed with code " + postResponseCode.toString())
                }
            }
        } catch(e) {
            context.println("Calling Triggears ${methodName} failed! " + e)
        }
    }

    static private void raiseIfTagRequested(List<RequestParam> requestedParams) {
        if (RequestParam.TAG in requestedParams) {
            throw new Exception("Triggear: Tag cannot be requested from push hooks")
        }
    }
}
