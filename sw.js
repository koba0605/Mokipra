/*
 * Mokipra Service Worker
 *
 * 【重要】ここではキャッシュを一切行わない。
 *
 * Chrome がホーム画面へのインストールを提案する条件として
 * Service Worker の登録が必要なため、その最小要件だけを満たしている。
 *
 * Streamlit は WebSocket でサーバーと常時通信し、静的ファイル名も
 * ビルドごとに変わる。ここでキャッシュを行うと、デプロイ後に
 * 古いJSが残って白画面になるなどの事故が起きやすい。
 * オフライン動作もサーバー通信前提のため成立しない。
 * したがって「素通しするだけ」が正しい実装になる。
 */

const VERSION = "mokipra-sw-v1";

self.addEventListener("install", (event) => {
  // 新しい Service Worker を即座に有効化する
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // 過去にキャッシュを作っていた場合に備えて、すべて破棄する
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  // キャッシュを挟まず、そのままネットワークへ流す
  event.respondWith(fetch(event.request));
});
