# K-Commerce Web

K-Commerce Web은 K-Commerce 에이전트 백엔드와 연결되는 Next.js 프론트엔드입니다.

English documentation is available in [README.md](README.md).

## 시작하기

의존성을 설치하고 개발 서버를 실행합니다.

```bash
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 엽니다.

프론트엔드는 기본적으로 `http://127.0.0.1:8000`의 에이전트 백엔드와 통신합니다.

## 백엔드

레포 루트에서 에이전트 백엔드를 실행합니다.

```bash
uv run k-commerce-agent
```

백엔드는 헬스 체크, MCP 도구 메타데이터, 스트리밍 채팅 엔드포인트를 제공합니다.
