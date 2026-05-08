// aRGus NDR — Jenkinsfile
// Pipeline CI/CD para cuando el servidor FEDER esté disponible
//
// Hardware target: servidor x86-64 dedicado (BACKLOG-BENCHMARK-CAPACITY-001)
// El Mac del founder NO puede ser parte de la cadena CI/CD de producción
// (DEBT-JENKINS-SEED-DISTRIBUTION-001)
//
// Consejo DAY 140 (8/8):
// - Gate ODR pre-merge obligatorio (DEBT-ODR-CI-GATE-001)
// - Nightly ODR check semanal
// - Gate código generado semanal (DEBT-GENERATED-CODE-CI-001)

pipeline {
    agent { label 'argus-server' }

    options {
        timeout(time: 2, unit: 'HOURS')
        disableConcurrentBuilds()
    }

    triggers {
        cron('0 3 * * 0')  // Domingo 3AM — ODR verification semanal
    }

    parameters {
        booleanParam(name: 'RUN_BENCHMARK', defaultValue: false,
            description: 'Capacity benchmark (requiere hardware físico)')
        booleanParam(name: 'DEPLOY_SEEDS', defaultValue: false,
            description: 'Deploy seeds (DEBT-JENKINS-SEED-DISTRIBUTION-001)')
    }

    stages {

        stage('Quick Check — Debug Build') {
            steps {
                sh 'vagrant destroy -f && vagrant up && make bootstrap && make test-all'
                sh 'make all 2>&1 | grep -c "warning:" | xargs test 0 -eq'
            }
        }

        stage('ODR Verification — Production Build') {
            // Pre-merge obligatorio + nightly semanal
            // Consejo DAY 140 (8/8) — DEBT-ODR-CI-GATE-001
            when { anyOf { changeRequest(); triggeredBy 'TimerTrigger' } }
            steps {
                sh 'make PROFILE=production all 2>&1 | tee build-production.log'
                sh 'grep -iE "odr|multiple.def|duplicate.symbol" build-production.log && exit 1 || echo "ODR check PASSED"'
            }
            post { always { archiveArtifacts artifacts: 'build-production.log', allowEmptyArchive: true } }
        }

        stage('Hardened VM — EMECAS prod') {
            when { branch 'main' }
            steps {
                dir('vagrant/hardened-x86') {
                    sh 'vagrant destroy -f && vagrant up && make hardened-full && make check-prod-all'
                }
            }
        }

        stage('Generated Code Check') {
            // Semanal — DEBT-GENERATED-CODE-CI-001
            when { triggeredBy 'TimerTrigger' }
            steps {
                sh 'make generate-protobuf || true'
                sh 'make all 2>&1 | grep -c "warning:" | xargs test 0 -eq && echo "Generated code CLEAN" || { echo "FAIL: new warnings in generated code"; exit 1; }'
            }
        }

        stage('Capacity Benchmark') {
            // Manual — BACKLOG-BENCHMARK-CAPACITY-001
            // Solo cuando hardware físico disponible
            when { expression { return params.RUN_BENCHMARK } }
            steps {
                sh 'make PROFILE=production sniffer && make PROFILE=production sniffer-libpcap'
                sh 'echo "TODO: tcpreplay benchmark protocol — BACKLOG-BENCHMARK-CAPACITY-001"'
            }
        }

        stage('Seeds Distribution') {
            // DEBT-JENKINS-SEED-DISTRIBUTION-001
            // NUNCA desde el Mac del founder
            when { allOf { branch 'main'; expression { return params.DEPLOY_SEEDS } } }
            steps {
                sh 'echo "TODO: DEBT-JENKINS-SEED-DISTRIBUTION-001 — generación local en nodo hardened"'
            }
        }
    }

    post {
        success { echo 'Pipeline PASSED — aRGus NDR' }
        failure  { echo 'Pipeline FAILED — revisar logs' }
        always   { sh 'vagrant suspend || true' }
    }
}
