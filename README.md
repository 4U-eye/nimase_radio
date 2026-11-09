# 二間瀬ラジオ

毎日のニュースを、毎朝短くまとめてお届けする放送局です。政治・経済・国際・地域の話題を5本、約2分で。スマホで聞いて、その場で出典（元の記事）も確認できます。

- プレーヤーは `index.html`。台本は `episodes/` の JSON、音声は `audio/` の MP3 です
- スマホ対応：PWA（`manifest.webmanifest`／`sw.js`）入り。公開先を Chrome で開けば「アプリをインストール」からホーム画面に追加できます
- 声：Muse の音声合成
- キャラクターとプレーヤーの仕組みは [myradio](https://github.com/monoradio102/myradio)（ものラジオ）のテンプレートを使っています

## 公開するとき

1. このフォルダの中身を自分の GitHub リポジトリに置く
2. `station.json` の `url` に公開先（`https://<you>.github.io/<repo>/`）、`repo` にリポジトリの URL を書く
3. `tools/publish.sh` で公開し、GitHub の Settings → Pages で `gh-pages` ブランチを配信元にする
4. リポジトリに topic `myradio-station` を付ける
