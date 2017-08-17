import groovy.json.JsonOutput

def call(Map args){
    sha = args.sha
    repository = args.repository
    state = args.state
    description = args.description
    url = args.url != null ? args.url : env.BUILD_URL
    context = args.context != null ? args.context : env.JOB_NAME
    try{
        withCredentials([string(credentialsId: 'triggear_token', variable: 'token')]) {
            def post = new URL(env.TRIGGEAR_URL + "status").openConnection();
            def payload = JsonOutput.toJson([
                sha: sha,
                repository: repository,
                state: state,
                description: description,
                url: url,
                context: context
            ]);
            println("Status create in Triggear (payload: " + payload + ")")
            post.setRequestMethod("POST");
            post.setDoOutput(true);
            post.setRequestProperty("Content-Type", "application/json");
            post.setRequestProperty("Authorization", "Token ${token}");
            post.getOutputStream().write(payload.getBytes("UTF-8"));
            def postRC = post.getResponseCode();
            if(postRC.equals(200)) {
                println(post.getInputStream().getText());
            } else {
                println("Status create in Triggear failed!")
            }
        }
    }
    catch(e){
        println("Status create in Triggear failed!" + e)
    }
}
