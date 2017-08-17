import groovy.json.JsonOutput

def call(Map args){
    eventType = args.eventType
    repository = args.repository
    labels = args.labels != null ? args.labels : []
    requested_params = args.requested_params != null ? args.requested_params : []
    try{
        withCredentials([string(credentialsId: 'triggear_token', variable: 'token')]) {
            def post = new URL(env.TRIGGEAR_URL + "register").openConnection();
            def payload = JsonOutput.toJson([
                eventType: eventType,
                repository: repository,
                jobName: env.JOB_NAME,
                labels: labels,
                requested_params: requested_params
            ]);
            println("Registration in Triggear (payload: " + payload + ")")
            post.setRequestMethod("POST");
            post.setDoOutput(true);
            post.setRequestProperty("Content-Type", "application/json");
            post.setRequestProperty("Authorization", "Token ${token}");
            post.getOutputStream().write(payload.getBytes("UTF-8"));
            def postRC = post.getResponseCode();
            if(postRC.equals(200)) {
                println(post.getInputStream().getText());
            } else {
                println("Registration in Triggear failed!")
            }
        }
    }
    catch(e){
        println("Registration in Triggear failed!" + e)
    }
}
