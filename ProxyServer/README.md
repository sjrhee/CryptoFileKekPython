# ProxyServer

이 프로젝트는 메인 애플리케이션(`CryptoFileKekPython`)이 외부에서 HSM 기능을 사용할 수 있도록 대행하는 리버스 프록시 및 API 서버입니다. Nginx를 통해 Client Certificate Authentication (mTLS)을 수행하고, 내부 Python 애플리케이션으로 요청을 전달합니다.

## 기능
- **mTLS 인증**: 클라이언트 인증서를 통한 보안 연결.
- **HSM 연동**: 실제 HSM 또는 시뮬레이션된 HSM을 사용하여 암호화/복호화 수행.
- **API 제공**: `/encrypt`, `/decrypt` 등의 엔드포인트 제공.

## 구조
- `src/`: Python 소스 코드
- `scripts/`: 실행 및 인증서 생성 스크립트
- `conf/`: Nginx 설정 파일
- `nginx.conf`: Nginx 설정 (루트 링크용)

## 시작 방법

1. **가상 환경 생성 및 의존성 설치**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **인증서 생성 (테스트용)**
   ```bash
   ./scripts/gen_certs.sh
   ```

3. **서버 시작**
   ```bash
   ./scripts/start.sh
   ```
   - Nginx: 8443 포트
   - Python App: 5001 포트

4. **서버 중지**
   ```bash
   ./scripts/stop.sh
   ```
