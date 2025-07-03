pipeline {
    agent any

    triggers {
        githubPush() // this enables webhook trigger
    }

    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/abhishek7467/diabetic-retinopathy-detector.git'
            }
        }

        stage('Setup') {
            steps {
                sh '''
                python3 -m venv venv
                source venv/bin/activate
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Flask App') {
            steps {
                sh '''
                source venv/bin/activate
                nohup python run.py &
                '''
            }
        }
    }
}
