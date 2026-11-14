/** @type {Map<string, Promise<void>>} */
const cache = new Map();

/**
 * UMD ベンダーを一度だけ読み込む。
 * @param {string} src
 * @returns {Promise<void>}
 */
export function loadScript(src) {
  const hit = cache.get(src);
  if (hit) return hit;

  const promise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => {
      cache.delete(src);
      reject(
        new Error(
          `ライブラリを読み込めませんでした: ${src}（client/vendor の同梱を確認してください）`
        )
      );
    };
    document.head.appendChild(s);
  });
  cache.set(src, promise);
  return promise;
}
