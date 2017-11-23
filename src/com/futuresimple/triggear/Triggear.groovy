package com.futuresimple.triggear

import groovy.json.JsonOutput

class Triggear implements Serializable {
    private Object context
    private GitHubRepo repository

    /**
     * Create a Triggear object for specific repository
     *
     * @param repositoryFullName full name of GitHub repository, e.g. "futuresimple/triggear"
     */
    Triggear(context, GitHubRepo repository) {
        this.context = context
        this.repository = repository
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
        sendRequestToTriggearService(ApiMethods.STATUS,
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
        sendRequestToTriggearService(ApiMethods.COMMENT,
        [
            sha: sha,
            repository: repository.repositoryFullName,
            jobName: context.env.JOB_NAME,
            body: body
        ])
    }

    void register(Registration request) {
        sendRequestToTriggearService(ApiMethods.REGISTER,
            [
                eventType           : request.registrationEvent.getEventName(),
                repository          : repository.repositoryFullName,
                jobName             : context.env.JOB_NAME,
                labels              : request.labels,
                requested_params    : request.requestedParameters.collect { it.getRequestParam() },
                branch_restrictions : request.branchRestrictions,
                change_restrictions  : request.changeRestrictions
            ]
        )
    }

    private void sendRequestToTriggearService(ApiMethods methodName, Map<String, Object> payload){
        try {
            context.withCredentials([context.string(credentialsId: 'triggear_token', variable: 'triggear_token')]) {
                URLConnection post = new URL("$context.env.TRIGGEAR_URL" + "${methodName.getMethodName()}").openConnection()
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
}
