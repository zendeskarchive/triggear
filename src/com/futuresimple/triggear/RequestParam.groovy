package com.futuresimple.triggear

enum RequestParam {
    BRANCH('branch'),
    SHA('sha'),
    TAG('tag')

    RequestParam(String requestParam) {
        this.requestParam = requestParam
    }
    private final String requestParam

    String getRequestParam() {
        return requestParam
    }
}
