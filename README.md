![Triggear](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/PhVcvTkZsFfrXz4WB18J9dnmq6JpON/triggear.png?Expires=1507399646&Signature=a0VmF~wDthgghf1Fz8HyLmUHEV57b0Y8uETNIoaS64faz~O~oFh8gNewJ-a3ypMRl3oCXhNGySPUWA9-Rx89rQzus7OfhoLE8mzameUfr11GOkAnrZQxeQrvBdnhxULc4Fy56Sf-JHmFCUX3ZflAS3DQ8bshPkTZjG0gbuuT5U9ZtUOldWpFyTf~3ksVt1eb3rXIH1D~iBqpgIHPXQ7i3lu44a8hwl~ZeDB2hgVJ55N7z0-5IYvMEEmHhuWW8eqwGsVpcMZmed2Z5xtIn8Lbh8deGBBIQzIy5K8GNMasFGJfHZFyc0D9zgsTwXaCEzR-b~e5a-IMEJI1gqEz7JLkdw__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA "Triggear")

### Triggear

__Triggear__ is a service that integrates GitHub with Jenkins pipelines. 
It provides ways of registering Jenkins pipelines for specific events
in GitHub and reporting job statuses and details back to GitHub.
If you ever thought about running Jenkins jobs without entering Jenkins
and remembering about all the jobs that you need to run - __Triggear__
is the guy you were looking for.

It should not be confused with GitHub plugins/service integration
with Jenkins as Triggear can do much more for you.

The example usage flow is following:

1. Jenkins pipeline sends registration request to Triggear, specifying what type of events in some repository should trigger it
2. Triggear saves registration in Mongo DB
3. At this point if event specified in registration request occurs in repository, Triggear will automatically trigger job that registered
4. After build is done, Triggear reports its status to GitHub - usually to commit/PR that triggered the job

For overview of Triggear features please read [6. Workflows](#workflows) section
### Table of Contents  
1. [Building Triggear](#build)
2. [Running tests](#test)
3. [Running Triggear as a service](#run)
4. [Setup in Jenkins](#jenkins)
5. [Setup in GitHub](#github)
6. [Workflows](#workflows)
   1. [Running jobs on pushes](#push)
   1. [Running jobs when PR is labeled](#label)
   1. [Running jobs on PR sync](#sync)
   1. [Re-running failed jobs](#rerun)
   1. [Setting custom commit statuses](#status)
   1. [Commenting PRs](#comment_pr)
   1. [Running jobs with tags](#tags_run)
   1. [Running jobs with PR comments](#comment_run)

Feel free to propose any new sections of docs by creating an issue. 
<a name="build"/>
###1. Building Triggear
To build triggear:
    
   * manually
   
You need to have Python 3.6.2 installed with pip. Then you download dependencies with:
```bash
pip install -r requirements.txt
```
 
   * with docker
```bash
docker build --tag triggear .
```
__Note:__ docker build runs all the unittests by default

   * with docker-compose
```bash
docker-compose build
```
__Note:__ docker-compose build runs all the unittests by default
<a name="test"/>
###2. Running tests

   * manually
```bash
PYTHONPATH=<PATH_TO_TRIGGEAR> py.test .
```

   * with docker
   
Included in build phase

   * with docker-compose
   
Included in build phase
<a name="run"/>
###3. Running Triggear as a service
To run Triggear you need to have running Jenkins instance and
GitHub repository (or many repositories). Then you need to
prepare `creds.yml` file like in [example](configs/creds-example.yml)
providing:
   
   * Jenkins URL
   * Jenkins user ID (will be used to trigger builds)
   * Jenkins API token for this user
   * GitHub token for your GitHub bot (needs write access to repositories)
   * Triggear token that will be used to authorize pipeline/github calls
   
There are couple of ways of running Triggear providing `creds.yml`

   * manually
In this case you need to have running mongo DB on localhost
```bash
CREDS_PATH=[PATH_TO_CREDS_YML] CONFIG_PATH=config.yml python3 app/main.py
```

   * with docker

In this case `creds.yml` needs to be in `<triggear-path>/configs` and
mongo DB needs to be running on localhost
```bash
docker run doc python app/main.py
```

   * with docker-compose

In this case `creds.yml` needs to be in `<triggear-path>/configs`
```bash
docker-compose up
```
This is of course easiest and preferred version of running Triggear
__not taking into consideration deploy to Kubernetes option.__
<a name="jenkins"/>
###4. Setup in Jenkins

Provided that you have running Triggear instance, we need to setup
it as a shared library in Jenkins, to let pipelines use registration
and status methods. To do it:

   1. Add `TRIGGEAR_URL` and global Jenkins variable. Its value should
   be something like `https://TRIGGEAR_URL/"
   
   2. Add Triggear repository as Shared Library in Jenkins. By doing
   so pipelines will get access to `vars` directory and will be
   able to use register and status update functions
   
   3. Add secret text with name `triggear_token` and value of triggear_token
   field from your `creds.yml`

__Note:__ Workflows section of docs assumes that you called Triggear
shared library as simply as `Triggear`
<a name="github"/>
###5. Setup in GitHub

__Note:__ this setup needs to be done in all repositories that
are supposed to trigger Jenkins jobs

   1. Add GitHub bot (the one that has API token used in `creds.yml`)
   to repository collaborators with __write__ permissions
   
   2. Add webhook to repository:
   
      - Set Payload URL to `https://TRIGGEAR_URL/github`
      - Set Content type to `application/json`
      - Set secret to value of your `triggear_token`
      - Select individual hook elements: __Issue comment__,
      __Pull request__, __Push__, __Create__
      
   3. Save - at this point test payload should be sent to 
   Triggear and response 200 should be returned to GitHub (can
   be seen in the bottom of webhook configuration where logs
   are)

At this point events from GitHub will be sent to Triggear.
<a name="workflows"/>
###6. Workflows

This section will describe possible user scenarios that Triggear
can execute.

__Note:__ for all trigger types Triggear uses value of `rerun_time_limit`
set in `./config.yml`. It is meant to throttle builds, not to run
some job 30 times in 1 minute just because someone furiously
pushes TYPO fixes to your repo. This limit can be modified manually.
<a name="push"/>
#### i. Running jobs on pushes

__Case #1__ You want your pipeline to be run on every push to 
repository X

To solve that you want your pipeline to use Triggear 
var `triggearRegister`:

```groovy
// Assuming you called this shared library "Triggear" in Jenkins
// Ommit this line if you add Triggear as shared library implicitly
@Library(['Triggear']) _

import com.futuresimple.triggear.RequestParam
import com.futuresimple.triggear.Triggear

Triggear triggear = new Triggear(this, 'org/repo')
triggear.registerForPushes([])
```

Now you need to run your job once to call register properly. From
then on every time someone pushes something to X this job will
be triggered.

__Case #2__ You want your pipeline to be run on every push to 
repository X and get branch and commit SHA of this push (e.g.
you want to run unittests job for every push)

To solve that you want your pipeline to use Triggear 
var `triggearRegister`:

```groovy
// Assuming you called this shared library "Triggear" in Jenkins
// Ommit this line if you add Triggear as shared library implicitly
@Library(['Triggear']) _

import com.futuresimple.triggear.RequestParam
import com.futuresimple.triggear.Triggear

Triggear triggear = new Triggear(this, 'X')
triggear.registerForPushes([RequestParam.BRANCH, RequestParam.SHA])
```

Now you need to run your job once to call register properly. From
then on every time someone pushes something to X this job will
be triggered with `branch` and `sha` parameters. __Remember that
your pipeline needs to accept `branch` and `sha` parameters,
otherwise execution will fail.

In both cases once your job is done, commit status in GitHub
will be set based on it's results:
![Commit status set by Triggear](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/vcBcAbCvUGpO710jcTZRwekM7PDyI7/commitstatus.png?Expires=1502464365&Signature=DYPWr0rlEQJYtZ18z4dhrOpGppSRxUYmVW1spTz2GGUOb-ZklfJP5Qy-BIe~PHjqMC6t6UHpX-kqCE06dr8tKFDLw8QCu5HYQOBf0s5IcNqL9Ro7cieEaCtfzSsdRgCgTOnFu7o3McY-nPCF87dTOtPNt5karvZgHEhSICyopQAYNxWKwQYw7AjIh~onCCyUrZY~gRfTGUQk1d4ReSxMA9HTLy2MCxMaW5RFM0A1duyU3XEt9xmYbGJH0hfksWwPcwm2TlJdfywU04zkjaucAlhZOC4ue9FVQDd94dWOD9hTWV--hvs0WfOlY1CEWQwVO7H3E~daoEGKX3jxh~jQCw__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA)

You can see, that job name is set as status context. When you click
on Details link you will be redirected to your job build URL.
<a name="label"/>
#### ii. Running jobs when PR is labeled

__Case #1__ You want your job to be run, when label Y is
set on PR in repository X

To solve that you want your pipeline to use Triggear 
var `triggearRegister`:

```groovy
// Assuming you called this shared library "Triggear" in Jenkins
// Ommit this line if you add Triggear as shared library implicitly
@Library(['Triggear']) _

import com.futuresimple.triggear.RequestParam
import com.futuresimple.triggear.Triggear

Triggear triggear = new Triggear(this, 'X')
triggear.registerForLabel('Y', [])
```

Now run you pipeline once to make register call. From then on
you can set label Y on your PR in X repository it will trigger
your pipeline.

__Case #2__ You want your job to be run, when label Y is
set on PR in repository X and get branch and current SHA of 
this PR (e.g. you want to deploy this branch to some environment)

To solve that you want your pipeline to use Triggear 
var `triggearRegister`:

```groovy
// Assuming you called this shared library "Triggear" in Jenkins
// Ommit this line if you add Triggear as shared library implicitly
@Library(['Triggear']) _

import com.futuresimple.triggear.RequestParam
import com.futuresimple.triggear.Triggear

Triggear triggear = new Triggear(this, 'X')
triggear.registerForLabel('Y', [RequestParam.BRANCH, RequestParam.SHA])
```

Now run you pipeline once to make register call. From then on
you can set label Y on your PR in X repository it will trigger
your pipeline setting `branch` and `sha` as parameters.
__Remember that your job needs to accept such parameters.__

In both cases once the job is done it will create or update
PR status with your job results:

![PR status by Triggear](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/EkilSm1JcvXYMet2zVHPKeTvK56XNv/PRstatus.png?Expires=1502464311&Signature=SFEbN476HAHBKb3doZrmmNcEtH6sQ67ieFKHeBxxslWCUWK9eaz6QaqQWWMda-0Di-M6gqQt-Ka9lwJKGOJdO7w~0KvpG2TmEr3ySv58yUlHNhIWkEPBgk0lb5JWw~C7t1BJ7mFLpe3iN9H6q90TBj7VmuimJreUPaESXZnvTf5fJbqJxFTDcNmr9xrQfwLQQuJFTB76H-1FSOLBlkBEbKjQVUitu0YgUqOhI6IGgXHzogFR2kqYwTMQYwxocRv-ECkzv7~uyIJ5RdX9Y86lh8VWHguJlQdRDJwnJr~jG-OQTq0rUOvXZ4i1AVBw5KdH9bPmh9p5uQQ27TGHBOiinQ__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA)

As you can see job name is again used as context. Details link
will redirect users from GitHub to your pipeline build.
<a name="sync"/>
#### iii. Running jobs on PR sync

__Case #1__ You want to run job registered for label Y on every
push to the PR labeled with Y (e.g. redeploy code on every PR
sync)

At first you need to register your job for label Y in repo X:

```groovy
// Assuming you called this shared library "Triggear" in Jenkins
// Ommit this line if you add Triggear as shared library implicitly
@Library(['Triggear']) _

import com.futuresimple.triggear.RequestParam
import com.futuresimple.triggear.Triggear

Triggear triggear = new Triggear(this, 'X')
triggear.registerForLabel('Y', [])
```

Then, you'll need a special label in your GitHub repo. It's name
should be `triggear-sync`.

Set label Y and `triggear-sync` on one of your PRs. 

![Triggear run on sync](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/3vpgIdsHplo0VARNjnCfLLRymrOg0X/triggearsync.png?Expires=1502466199&Signature=O7T7U0nmW~xTd2oLsE9L9-1RTtx~JPV8GzMXBH6kBzgfzdq91H4xMh3zhUL6Q2imR5cwMnTDseK8G6WJOXJL2UMbuTZa9WHY7NOkmvagyVxVbnfSzns8-0FGSk9a6DYDVb4zcrz1Y01IfU5GcsXO8bDG04fa5wi4Ipu5srH8Odc4LeGyLX5FXnGDFXbCQVWSox-ISr9ekY16APpnS8K4oaAEevT5knG2qdXsPsX2f7vbdlmPQJ6FIqocXzl0IVI9~dkvDkz3Q5DMPaNcSM8nBsRVVqr16fYTBnzonPnaFIZ9GCJIk6lCP4ENfKYttn9~ZFI8hSvWj6J5fGpgXAkpTg__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA)

From then on
every push to this PRs branch will trigger your job. Removing
`triggear-sync` label will stop this behaviour.
<a name="rerun"/>
#### iv. Re-running failed jobs

__Case #1__ You labeled PR with label Y which triggered some jobs
and reported status back to PR. Commit status is set to fail,
as your job failed and you know that it is not related to code. 
You want to rerun it without having to push something to PR.

To do this simply open GitHub PR and write comment:
```
Triggear resync <sha>
```

By doing so following behaviour will start:
 - Triggear will look on your PR and check it's labels
 - Triggear will run the job that failed giving it `branch` and `sha`
 parameters according to what you specified in PR/comment
 - Once the job is done Triggear will update commit status
 according to job results
 
Voila - no pushes/labels caused full rerun of jobs registered
with context of specified SHA.

![Triggear resync](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/G34ADXnkixu0wydeWFXZSOlAVQTZcI/triggearresync.png?Expires=1502469108&Signature=Po-BPBmkwNYFm1X2WV2NkQS97wPe8FiA3~lPKzWMBjkFfJoLbuPURayCpn8mfFRgUm8auwNew4AtdryyTqLCo20K6Ww0EqQ-MPj93KnI6EezcU-JOy2VL3hvFUgtz6ylKHy65miClWiYqvqkJdMMj35QcW1phQCu83ON5HlNs4hlrVBxNN3s6fjX2hd5BrALYsXMMSR374M0L1t2OovjGC1yWT3Jirvfs~Po02YYIud4Ic3B9us6DhP2upkzUXDNEXwaO5L~W0JSAd8OZSBHgvEdrIYHz74qL7F2AbFZXY-hPoVXVEOJ10Dfuxb4YN4zC9pE-4YL9k17U1QkdB2sGQ__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA)
<a name="status"/>
#### v. Setting custom commit statuses

__Case #1__ Some event (push/labeled) triggered your job and it
produced an artifact in Jenkins available at some URL. You want
to make this URL visible as one of commits statuses, not to
dig through Jenkins UI. Common use case for us at Base is that
we want link to unittest report to be visible directly in GitHub
without digging through Jenkins build UI

So let's assume that unittests report is stored at `$BUILD_URL/report`.
Your job is registered for pushes and gets SHA from Triggear 
and you want this report to be visible in GitHub for every commit.

To do so - in your Pipeline, once it's done call `triggearStatus`
var:

```groovy
import com.futuresimple.triggear.CommitState

// this is the case when your job handles sha as param
triggear.addCommitStatus(params.sha, 
    currentBuild.result == "SUCCESS" ? CommitState.SUCCESS : CommitState.FAILURE, 
    "Unittests report for commit ${params.sha}",
    "Unittests report",
    "${BUILD_URL}report"
)
```

By doing so, every commit will have new custom status once the job
is done:

![Triggear custom SHA status](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/tfivuyjLZcpyUXjHzGsYfBlG5ixtFL/customstatus.png?Expires=1502467263&Signature=ZHpxEvD9Es0OHuvOO5ttmMS2w4XCH1B9nyh~ASGa9Dx6DkriGIhpRG-Rivy-k1nLSABgG4K8f~jMSzlV3A2nX4BmwCCAkwU-CBNEUszVU0bRkWO7Ol2fcJ2T1sJ73uKoRNqDFXa127rK9T-nSTK0z8QA0JiSK8Eaue7K0rNwHs8N4qUObgSZkK71bqoJHddzlyrm3zCYeNt7a97LZ1K2KkO26yKmXLe2DwIJ3yKXu43Dv1gM2AisY20nJw57X6NwsE8c0myvTeTWJw5sbwM4LudTCpPtO9d2S3CHQHKN8LvflQHW00fMEUvZv1i9~4-kZTv0IH2sg2PwFP0UuQ01ZQ__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA)

Of course this status will only be visible __after__ job is done
so there won't be any pending state visible in GH for it at any time.
<a name="comment_pr"/>
#### vi. Commenting PRs

__Case #1__ You want your job to create a comment on PR/commit with some
details that are too long to be presented as commit statuses

So the common case for us at Base is that we won't to present some
information about build that are simply too long for statuses in GH
(remember: it has content length limit). It can be info about
binary size, build time or anything non-status-like.

To do so, use `triggearComment` var at some point in your
pipeline:

```groovy
// this is the case when your job handles sha as param
triggear.addComment(params.sha, 'Very important info about the build')
```

By doing so you will see the following results:

![Triggear custom commit](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/REUYueMgkNwHjWU0jzJOl5QMAntftJ/comment.png?Expires=1502471393&Signature=k2IrYunyIEMe6fmK5EaWzNYTY7Zy0mXAnNzEClhFjghc2x0s01IFPfwRLjIqQ~w~ccVqN7cbn8QZqlqbeu0h5yuG5LFgtiWMgsw8pJ2Lektj-qxSSO3devbYOIMC7MfdKRbstAFn4gc8rDuOYRSD~W27mY9DrG~ZSpVsr5mXl24EQtdPRK8zSTlliyrO7nGZW7Hz4sa0e~NYGfbjPnHC-nd5CRtpOJhZcqAfArQtDSFxJYbd9eexkXRgD8IQe8GUDwOvDIGLuGB6j3gZNGQrifPKF~seHUmLls04-eqsnT5ZjJhCYkHeZEnhmlH8XC5aN2JyuR6cNgw0hUUEXONYxg__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA)

Of course one pipeline can create multiple comments.
<a name="tags_run"/>
#### vii. Running jobs with tags
__Case #1__ You want your job to run at the time when someone
pushes a new tag to repository. At Base we use that to create
app's with given tag for reference

To do so you need to register your job for `tagged` events in repo X:

```groovy
// Assuming you called this shared library "Triggear" in Jenkins
@Library(['Triggear']) _

import com.futuresimple.triggear.RequestParam
import com.futuresimple.triggear.Triggear

Triggear triggear = new Triggear(this, 'X')
triggear.registerForTags([RequestParam.BRANCH, RequestParam.SHA, RequestParam.TAG])
```

By running your job once, you'll enable functionality of running
your job every time new tag is pushed to origin. Your job will
receive tag name and branch/sha of tagged commit as parameters, so
make sure that it accepts them and can handle such params.
<a name="comment_run"/>
#### viii. Running jobs with PR comments

__Case #1__ You want to run specific job by writing comment on
you PR, not having to enter Jenkins

This is rather uncommon case but maybe you remember your job name
and it's parameters, but you don't want to enter Jenkins UI and you
want to run it with PR comment?

So in PR type following comment:

```
Triggear run jobDir/jobName param1=value1 param2=value2
```

If your job has no params simply remove params specification
from that line. Once the job is executed you will get a PR comment
with it's status and URL to it.

![Triggear run by comment](https://d1ro8r1rbfn3jf.cloudfront.net/ms_147854/gG77zYRx1OkBwUq5jrqrQmpL33AyLy/run-by-comment.png?Expires=1502468864&Signature=BfZT74y168DtsUm4cMegy1IruwolTeffERmdOME25yFenx3rdO86eIO-BV-WYa8INYUiu9NSLqVqMBqwZq1kImqI-Gs6m8GmQuan2qFW5RU2wpwWhimvwfyQi6pPYibff9I~ha-N~B8HvcDqs09q4JhWGoYkZYMI7n4Ap7XWDeTJgpFkAkf9-suJxAd1iXFPhJzJnU-UuG-Uwprboy~yAG3nrIuOVk2ymjktz8zEexnEEwgXmClY~nYs1aYMtVFa~mShbWhAg7EuwU-ihcbSdnGhjZCLop1Vi8e~PSaJ17yo2Y9iYmWhNDDbIYHsRTCvdfyf0FxlJ9PYPyLxCyTwDw__&Key-Pair-Id=APKAJHEJJBIZWFB73RSA)

