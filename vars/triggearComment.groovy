import groovy.json.JsonOutput

def call(Map args){
    sha = args.sha
    repository = args.repository
    body = args.body
    try{
        withCredentials([string(credentialsId: 'triggear_token', variable: 'token')]) {
            def post = new URL(env.TRIGGEAR_URL + "comment").openConnection();
            def payload = JsonOutput.toJson([
                sha: sha,
                repository: repository,
                jobName: env.JOB_NAME,
                body: body
            ]);
            println("Commenting commit by Triggear (payload: " + payload + ")")
            post.setRequestMethod("POST");
            post.setDoOutput(true);
            post.setRequestProperty("Content-Type", "application/json");
            post.setRequestProperty("Authorization", "Token ${token}");
            post.getOutputStream().write(payload.getBytes("UTF-8"));
            def postRC = post.getResponseCode();
            if(postRC.equals(200)) {
                println(post.getInputStream().getText());
            } else {
                println("Commenting commit by Triggear failed!")
            }
        }
    }
    catch(e){
        println("ommenting commit by Triggear failed!" + e)
    }
}
