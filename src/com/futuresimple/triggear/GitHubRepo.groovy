package com.futuresimple.triggear

class GitHubRepo implements Serializable {
    String organizationName
    String repositoryUrl
    String repositoryName
    String repositoryFullName
    
    /**
     * Creates a simple 'DTO' which carries couple of forms of GitHub repo URL and names.
     *
     * @param repositoryName Short repository name, e.g. for git@github.com:futuresimple/triggear pass here 'futuresimple' and 'triggear'
     */
    GitHubRepo(String organizationName, String repositoryName){
        this.organizationName = organizationName
        this.repositoryUrl = "git@github.com:${organizationName}/${repositoryName}.git"
        this.repositoryName = repositoryName
        this.repositoryFullName = "${organizationName}/${repositoryName}"
    }
}
