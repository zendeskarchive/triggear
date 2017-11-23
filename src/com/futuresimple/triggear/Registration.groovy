package com.futuresimple.triggear

import groovy.transform.PackageScope

class Registration {
    @PackageScope EventType registrationEvent
    @PackageScope List<String> labels = []
    @PackageScope List<RequestParam> requestedParameters = []
    @PackageScope List<String> changeRestrictions = []
    @PackageScope List<String> branchRestrictions = []

    private Registration(EventType type){
        registrationEvent = type
    }

    private void addLabel(String label){
        labels.add(label)
    }

    private void addChangeRestriction(String pathPrefix){
        changeRestrictions.add(pathPrefix)
    }

    private void addBranchRestriction(String branch){
        branchRestrictions.add(branch)
    }

    private void addBranchAsParameter(){
        requestedParameters.add(RequestParam.BRANCH)
    }

    private void addShaAsParameter(){
        requestedParameters.add(RequestParam.SHA)
    }

    private void addTagAsParameter(){
        requestedParameters.add(RequestParam.TAG)
    }

    static PushBuilder forPushes(){
        return new PushBuilder()
    }

    static TagBuilder forTags(){
        return new TagBuilder()
    }

    static LabelBuilder forLabels(){
        return new LabelBuilder()
    }

    static PrBuilder forPrOpened(){
        return new PrBuilder()
    }

    static class PushBuilder implements Builder {
        PushBuilder(){
            eventType = EventType.PUSH
        }

        PushBuilder addBranchRestriction(String branch){
            request.addBranchRestriction(branch)
            return this
        }

        PushBuilder addChangeRestriction(String pathPrefix){
            request.addChangeRestriction(pathPrefix)
            return this
        }
    }

    static class TagBuilder implements Builder {
        TagBuilder(){
            eventType = EventType.TAG
        }

        TagBuilder addTagAsParameter(){
            request.addTagAsParameter()
            return this
        }

        TagBuilder addBranchRestriction(String branch){
            request.addBranchRestriction(branch)
            return this
        }
    }

    static class LabelBuilder implements Builder {
        LabelBuilder(){
            eventType = EventType.LABEL
        }

        LabelBuilder addLabel(String label){
            request.addLabel(label)
            return this
        }
    }

    static class PrBuilder implements Builder {
        PrBuilder(){
            eventType = EventType.PR_OPEN
        }
    }

    private trait Builder {
        EventType eventType
        Registration request

        Registration getRequest(){
            if(request == null){
                request = new Registration(eventType)
            }
            return request
        }

        Builder addBranchAsParameter(){
            getRequest().addBranchAsParameter()
            return this
        }

        Builder addShaAsParameter(){
            getRequest().addShaAsParameter()
            return this
        }

        Registration build(){
            return request
        }
    }
}
