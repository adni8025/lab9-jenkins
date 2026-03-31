pipeline {
    agent any

    triggers {
        githubPush()
        cron('H 2 * * *')
    }

    environment {
        TOOL_VENV = '/opt/jenkins-tools/venv'
        EMAIL_TO = 'adni8025@colorado.edu'
    }

    stages {
        stage('Install Dependencies') {
            steps {
                sh '''
                    sudo -n apt update
                    sudo -n apt install -y python3 python3-pip python3-venv git
                    if [ ! -d "$TOOL_VENV" ]; then
                        sudo -n python3 -m venv "$TOOL_VENV"
                    fi
                    sudo -n "$TOOL_VENV/bin/pip" install --upgrade pip
                    sudo -n "$TOOL_VENV/bin/pip" install ncclient pandas ipaddress netaddr prettytable pylint netmiko
                '''
            }
        }

        stage('PEP8 and Pylint') {
            steps {
                script {
                    int pylintStatus = sh(
                        script: '''
                            set +e
                            "$TOOL_VENV/bin/pylint" --disable=C0114,C0115,C0116 netman_netconf_obj2.py > pylint.log 2>&1
                            status=$?
                            cat pylint.log
                            exit $status
                        ''',
                        returnStatus: true
                    )
                    recordIssues(
                        enabledForFailure: true,
                        tools: [pyLint(pattern: 'pylint.log', id: 'pylint', name: 'PyLint')],
                        qualityGates: [[threshold: 5, type: 'TOTAL', criticality: 'FAILURE']]
                    )
                    if (pylintStatus != 0) {
                        error('Pylint failed')
                    }
                }
            }
        }

        stage('Run Application') {
            steps {
                sh '''
                    "$TOOL_VENV/bin/python" netman_netconf_obj2.py
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    "$TOOL_VENV/bin/python" -m unittest -v test_lab9
                '''
            }
        }
    }

    post {
        success {
            emailext(
                to: "${EMAIL_TO}",
                subject: "SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Job ${env.JOB_NAME} build ${env.BUILD_NUMBER} succeeded. Console output: ${env.BUILD_URL}console",
                attachLog: true
            )
        }
        failure {
            emailext(
                to: "${EMAIL_TO}",
                subject: "FAILURE: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Job ${env.JOB_NAME} build ${env.BUILD_NUMBER} failed. Console output: ${env.BUILD_URL}console",
                attachLog: true
            )
        }
    }
}
