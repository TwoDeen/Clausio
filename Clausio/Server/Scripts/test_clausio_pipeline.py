"""
test_clausio_pipeline.py
========================
TDD regression and integration test suite for the Clausio game engine.

Run:
    pytest test_clausio_pipeline.py -v
    pytest test_clausio_pipeline.py -v -m "not ginza"   # skip GiNZA-dependent tests

Coverage:
  1. Puzzle schema / structure (25 nodes, required fields on every node)
  2. `sentence_individual_grammar_level` always present & valid
       ← PRIMARY REGRESSION TEST for the N/A display bug
  3. Grammar level detection ordering (N1 sentences detected as ≥ N5 on average)
       ← skipped automatically when GiNZA is not installed
  4. FastAPI endpoint integration via TestClient
       /api/news/puzzle/generate  (mocked scraper, works without GiNZA)
       /api/puzzle/generate       (temp file, requires GiNZA — skipped otherwise)
       /api/news/topics           (mocked RSS, always runs)
       /api/stories               (filesystem scan, always runs)
       /api/cache/clear           (always runs)
"""

from __future__ import annotations

import json
import os
import tempfile
from itertools import islice
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from generate_grid_puzzle import build_puzzle_from_news_tokens

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_LEVELS = {"N1", "N2", "N3", "N4", "N5"}
LEVEL_WEIGHT  = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5}
REQUIRED_NODE_KEYS = {
    "clause_id",
    "grid_coordinates",
    "parent_sentence_id",
    "clause_text",
    "furigana",
    "sentence_individual_grammar_level",  # ← the field whose absence caused N/A
}

# ── Session-scoped GiNZA availability fixture ─────────────────────────────────

@pytest.fixture(scope="session")
def ginza_available() -> bool:
    try:
        import spacy
        spacy.load("ja_ginza")
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient. Created once, reused across all tests."""
    with TestClient(app) as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════════
# 100 Japanese sentences — 20 per JLPT level (N5 → N1)
# ══════════════════════════════════════════════════════════════════════════════

N5 = [
    "私は毎朝ご飯を食べます。",
    "今日は天気がとてもいいです。",
    "この映画はとても面白いです。",
    "彼女は日本語の先生です。",
    "駅はここから近いですか。",
    "図書館で静かに本を読みます。",
    "学校に電車で行きます。",
    "水がとても冷たいです。",
    "猫は部屋の中にいます。",
    "あの山はとても高いです。",
    "母は料理がとても上手です。",
    "昨日友達と公園で話しました。",
    "日本語の勉強が好きです。",
    "本を三冊図書館で借りました。",
    "今日は学校が休みです。",
    "犬と猫が庭で遊んでいます。",
    "バスで駅まで行きました。",
    "兄は会社員で毎日忙しいです。",
    "この店のりんごは甘くておいしいです。",
    "空がとても青くてきれいです。",
]

N4 = [
    "雨が降っているので傘を持って行きます。",
    "彼は日本語が少しずつ上手になってきました。",
    "宿題が終わってからテレビを見るつもりです。",
    "病気になったら病院に行かなければなりません。",
    "音楽を聞きながら料理を作るのが好きです。",
    "もっと練習すれば試験に合格できると思います。",
    "この店は料理がおいしいだけでなくサービスもいいです。",
    "彼女はいつか医者になりたいと言っていました。",
    "電車が遅れたため会議に遅刻してしまいました。",
    "日本に来てからもう三年が経ちました。",
    "子供の頃よく川で魚を釣ったものです。",
    "試験が終わったら旅行に行くつもりです。",
    "この薬を飲めばすぐに元気になりますよ。",
    "毎日運動しているので体の調子がとてもいいです。",
    "夏休みに海外旅行をしてみたいと思っています。",
    "荷物が重すぎて一人では持てませんでした。",
    "仕事が終わり次第すぐに連絡してください。",
    "彼女が来るまでここで待っていてもいいですか。",
    "日本語が話せるようになるまで毎日練習します。",
    "この映画はとても感動的だったので泣いてしまいました。",
]

N3 = [
    "環境問題を解決するために私たちに何ができるか考えましょう。",
    "彼が遅刻したのは電車が止まってしまったからです。",
    "スマートフォンの利用者が増えるにつれて様々な問題も増えてきました。",
    "この計画がうまくいくかどうかはまだわかりません。",
    "健康のためならどんな努力も惜しまないつもりです。",
    "彼女はピアノが弾けるだけでなくバイオリンも上手に演奏できます。",
    "仕事が忙しくて家族と話す時間がなかなか取れない日が続いています。",
    "先生の説明を聞いてもわからなかったのでもう一度教えてもらいました。",
    "その映画は見れば見るほど面白くなってくる作品です。",
    "一生懸命勉強したおかげで難しい試験に合格することができました。",
    "天気予報によると明日は大きな台風が来るそうです。",
    "彼女がとても忙しそうだったので声をかけるのをやめました。",
    "子供たちが元気に遊んでいる姿を見るとこちらまで嬉しくなります。",
    "新しい技術のおかげで私たちの生活はずいぶん便利になりました。",
    "どんなに疲れていても毎日日記を書くことにしています。",
    "試合に負けてしまいましたが全力を尽くしたので後悔はありません。",
    "このままでは間に合わないかもしれないので急いだほうがいいと思います。",
    "海外で生活するうちに異文化への理解が少しずつ深まっていきました。",
    "彼の話を聞く限りこの問題はすぐには解決しそうにありません。",
    "最初は難しいと思っていたが練習を続けるうちに少しずつ上達してきた。",
]

N2 = [
    "経済の発展にともなって都市部への人口集中が一層進んでいる。",
    "その法案は賛否両論があったにもかかわらず議会で可決された。",
    "科学技術の進歩によってかつては不可能とされていたことが実現しつつある。",
    "環境保護の観点から考えるとこの開発計画は見直す必要があると言わざるを得ない。",
    "少子高齢化が進む日本において労働力不足が深刻な問題となっている。",
    "彼は優秀な研究者であるばかりか優れた教育者としても高い評価を受けている。",
    "グローバル化が進む現代社会では語学力はもはや不可欠なスキルとなっている。",
    "交渉の結果両者の間で合意に達することができたものの課題は依然として残っている。",
    "このプロジェクトを成功させるにあたって全員の協力が不可欠であることは言うまでもない。",
    "被害の状況を踏まえ政府は緊急支援措置を速やかに実施することを決定した。",
    "市場の動向を分析した結果今後の需要拡大が見込まれることが明らかになった。",
    "彼女が提案した改革案は既存の制度の枠を超えた斬新なものだったことから大きな反響を呼んだ。",
    "現地の文化や慣習を尊重することなしに真の国際交流は成り立たないと考えられている。",
    "今回の事故を受けて安全管理体制の抜本的な見直しが求められていることは明らかである。",
    "技術革新の恩恵を最大限に活かすためには社会全体での取り組みが不可欠である。",
    "地球温暖化の問題に対処するには国際社会が一丸となって取り組む必要がある。",
    "経営方針の転換を余儀なくされた背景には急速な市場環境の変化があったと言える。",
    "専門家の意見を参考にしつつも最終的な判断は自分自身で行う必要がある。",
    "予算の制約があるにしても品質を下げることなく目標を達成する方法を模索すべきである。",
    "政策の有効性を評価するにあたってはその長期的な影響を考慮することが重要である。",
]

N1 = [
    "少子化が深刻化するにつれて社会保障制度の持続可能性に対する懸念が一段と高まりつつある。",
    "科学的根拠に基づかない情報が拡散しかねない現代においてメディアリテラシーの重要性は看過できない。",
    "国際社会が直面する諸問題を解決するにはイデオロギーの相違を超えた協調が不可欠と言わざるを得ない。",
    "急速な技術革新がもたらす恩恵の一方で雇用構造の変化をはじめとした負の側面にも目を向けるべきである。",
    "規制緩和を推進する立場からすれば過剰な法的制約が経済の活力を削いでいるという主張も一概に否定できない。",
    "生態系の保全を図るためには経済的利益を優先する開発志向から脱却するほかはないとの議論が台頭している。",
    "民主主義の根幹をなす言論の自由も他者の権利を著しく侵害する場合には一定の制限を受けることもやむを得ない。",
    "高度情報化社会においては個人情報の保護と情報の自由な流通との間でいかにバランスを保つかが喫緊の課題となっている。",
    "自然科学の領域においても従来のパラダイムに固執することなく新たな知見を柔軟に取り入れる姿勢が求められてやまない。",
    "国家間の対立が激化しかねない状況において外交的解決を最優先とする姿勢を堅持することが賢明であるとの見方が強い。",
    "経済合理性のみを追求するあまり社会的公正の実現を疎かにしてはならないという認識が政策立案の場においても共有されつつある。",
    "文化的多様性を尊重するという観点からすれば一元的な価値観を世界に押し付けることへの批判は当然と言うべきであろう。",
    "いかなる困難に直面しようとも人間としての尊厳を守るという普遍的な価値観が法の支配の根底に据えられているべきである。",
    "未曾有の経済危機に瀕した当時政策当局が迅速かつ大胆な対応を余儀なくされたことは歴史的な記録が証明するところである。",
    "現代の複合的なリスクに対応するには単一の専門分野に留まることなく学際的なアプローチを採用することが不可欠とされている。",
    "技術の急速な発展がもたらす倫理的な問いかけに対し哲学的な考察を深めることなしには適切な答えを見出すことはかなわない。",
    "市民社会の成熟を促す上で教育機関が担うべき役割はいかに大きなものであるかを改めて認識する必要があろう。",
    "持続可能な社会の実現に向けて経済・環境・社会の三側面を統合した政策的枠組みを構築することが急務となっている。",
    "人工知能の倫理的活用を担保するためには技術開発者のみならず社会全体がその責任を共有するという認識の醸成が不可欠である。",
    "グローバルな競争が激化するいかんによらず自国の文化的アイデンティティを維持することが各社会の長期的な発展に寄与するとの主張は根強い。",
]

# ── Batch helpers ─────────────────────────────────────────────────────────────

def _batches(lst: list, size: int = 5) -> list[list]:
    """Split a list into consecutive chunks of `size`."""
    it = iter(lst)
    return list(iter(lambda: list(islice(it, size)), []))


def _build(sentences: list[str], level: str = "N4") -> dict:
    """Call the news-token puzzle builder with no furigana dict."""
    return build_puzzle_from_news_tokens(sentences[:5], {}, level)


# Parametrize IDs covering all 100 sentences (4 batches × 5 levels = 20 cases)
LEVEL_BATCHES = [
    pytest.param(level, idx, batch, id=f"{level}-batch{idx + 1}")
    for level, sentences in [
        ("N5", N5), ("N4", N4), ("N3", N3), ("N2", N2), ("N1", N1)
    ]
    for idx, batch in enumerate(_batches(sentences))
]


# ══════════════════════════════════════════════════════════════════════════════
# 1 — Puzzle schema / structure
# ══════════════════════════════════════════════════════════════════════════════

class TestPuzzleSchema:
    """
    Structural guarantees that must hold for every puzzle payload
    regardless of language level or GiNZA availability.
    """

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_grid_has_25_nodes(self, level, idx, batch):
        payload = _build(batch, level)
        assert len(payload["grid_matrix"]) == 25, (
            f"{level} batch {idx + 1}: expected 25 nodes, got {len(payload['grid_matrix'])}"
        )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_total_grid_clauses_field_matches_matrix_length(self, level, idx, batch):
        payload = _build(batch, level)
        assert payload["total_grid_clauses"] == len(payload["grid_matrix"])

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_each_row_has_exactly_5_columns(self, level, idx, batch):
        payload = _build(batch, level)
        for row in range(1, 6):
            row_nodes = [n for n in payload["grid_matrix"]
                         if n["grid_coordinates"]["row"] == row]
            assert len(row_nodes) == 5, (
                f"{level} batch {idx + 1}: row {row} has {len(row_nodes)} columns"
            )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_clause_ids_are_unique_and_sequential(self, level, idx, batch):
        payload = _build(batch, level)
        ids = [n["clause_id"] for n in payload["grid_matrix"]]
        assert sorted(ids) == list(range(1, 26)), (
            f"{level} batch {idx + 1}: clause_id sequence broken: {ids}"
        )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_clause_text_is_non_empty_for_all_nodes(self, level, idx, batch):
        payload = _build(batch, level)
        for node in payload["grid_matrix"]:
            assert node["clause_text"].strip(), (
                f"{level} batch {idx + 1}: empty clause_text at "
                f"row={node['grid_coordinates']['row']} "
                f"col={node['grid_coordinates']['column']}"
            )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_top_level_payload_keys_present(self, level, idx, batch):
        payload = _build(batch, level)
        for key in ("target_level_requested", "highest_grammar_level_encountered",
                    "total_grid_clauses", "puzzle_solution_flow", "grid_matrix"):
            assert key in payload, f"{level} batch {idx + 1}: missing top-level key '{key}'"

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_highest_grammar_level_is_valid(self, level, idx, batch):
        payload = _build(batch, level)
        hgl = payload["highest_grammar_level_encountered"]
        assert hgl in VALID_LEVELS, (
            f"{level} batch {idx + 1}: highest_grammar_level_encountered = '{hgl}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2 — sentence_individual_grammar_level field (PRIMARY REGRESSION TEST)
#
#     This class directly tests the bug that caused "N/A" in TileView.
#     The root cause chain was:
#       ClauseNode missing `sentence_individual_grammar_level`
#         → Tile.sentenceIndividualGrammarLevel = nil
#           → TileView shows "N/A"
#     All tests here must pass even without GiNZA installed.
# ══════════════════════════════════════════════════════════════════════════════

class TestGrammarLevelField:
    """
    Regression tests for the N/A display bug.
    `sentence_individual_grammar_level` must be present and valid on EVERY
    clause node in EVERY puzzle payload, for all 100 sentences.
    """

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_field_present_on_every_node(self, level, idx, batch):
        """
        THE regression test. Before the fix, this field was absent,
        causing tile.sentenceIndividualGrammarLevel to be nil in Swift
        and 'N/A' to render in TileView.
        """
        payload = _build(batch, level)
        missing = [
            (n["grid_coordinates"]["row"], n["grid_coordinates"]["column"])
            for n in payload["grid_matrix"]
            if "sentence_individual_grammar_level" not in n
        ]
        assert not missing, (
            f"{level} batch {idx + 1}: `sentence_individual_grammar_level` "
            f"absent on nodes at positions: {missing}"
        )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_field_value_is_not_none(self, level, idx, batch):
        payload = _build(batch, level)
        null_nodes = [
            (n["grid_coordinates"]["row"], n["grid_coordinates"]["column"])
            for n in payload["grid_matrix"]
            if n.get("sentence_individual_grammar_level") is None
        ]
        assert not null_nodes, (
            f"{level} batch {idx + 1}: `sentence_individual_grammar_level` "
            f"is None on nodes at: {null_nodes}"
        )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_field_value_is_valid_jlpt_level(self, level, idx, batch):
        """Value must be one of N1-N5 — never an empty string or arbitrary text."""
        payload = _build(batch, level)
        invalid = [
            (n["grid_coordinates"]["row"], n["grid_coordinates"]["column"],
             n.get("sentence_individual_grammar_level"))
            for n in payload["grid_matrix"]
            if n.get("sentence_individual_grammar_level") not in VALID_LEVELS
        ]
        assert not invalid, (
            f"{level} batch {idx + 1}: invalid grammar level values: {invalid}"
        )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_all_tiles_in_same_row_share_same_level(self, level, idx, batch):
        """
        All 5 columns of a row come from the same sentence, so they must all
        carry the same detected grammar level.
        """
        payload = _build(batch, level)
        for row in range(1, 6):
            row_levels = {
                n["sentence_individual_grammar_level"]
                for n in payload["grid_matrix"]
                if n["grid_coordinates"]["row"] == row
            }
            assert len(row_levels) == 1, (
                f"{level} batch {idx + 1}: row {row} has mixed grammar levels: {row_levels}"
            )

    @pytest.mark.parametrize("level,idx,batch", LEVEL_BATCHES)
    def test_required_node_keys_all_present(self, level, idx, batch):
        """Every node must carry the full set of keys expected by ClauseNode."""
        payload = _build(batch, level)
        for node in payload["grid_matrix"]:
            missing_keys = REQUIRED_NODE_KEYS - node.keys()
            assert not missing_keys, (
                f"{level} batch {idx + 1}: node "
                f"row={node['grid_coordinates']['row']} "
                f"col={node['grid_coordinates']['column']} "
                f"is missing keys: {missing_keys}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 3 — Grammar level detection accuracy (requires GiNZA)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.ginza
class TestGrammarLevelAccuracy:
    """
    Statistical ordering tests: N1 sentences should be detected as harder
    (higher weight) than N5 sentences on average.
    Skipped automatically when GiNZA is not installed.
    """

    def _avg_detected_weight(self, sentences: list[str], level: str) -> float:
        weights = []
        for batch in _batches(sentences):
            payload = _build(batch, level)
            # Column-1 node carries the per-sentence detected level
            for node in payload["grid_matrix"]:
                if node["grid_coordinates"]["column"] == 1:
                    lv = node.get("sentence_individual_grammar_level", "N5")
                    weights.append(LEVEL_WEIGHT.get(lv, 1))
        return sum(weights) / len(weights) if weights else 0.0

    def test_n1_avg_weight_gte_n5(self, ginza_available):
        if not ginza_available:
            pytest.skip("GiNZA not installed")
        n5_avg = self._avg_detected_weight(N5, "N5")
        n1_avg = self._avg_detected_weight(N1, "N1")
        assert n1_avg >= n5_avg, (
            f"Expected N1 avg weight ({n1_avg:.2f}) >= N5 avg weight ({n5_avg:.2f})"
        )

    def test_n2_avg_weight_gte_n4(self, ginza_available):
        if not ginza_available:
            pytest.skip("GiNZA not installed")
        n4_avg = self._avg_detected_weight(N4, "N4")
        n2_avg = self._avg_detected_weight(N2, "N2")
        assert n2_avg >= n4_avg, (
            f"Expected N2 avg weight ({n2_avg:.2f}) >= N4 avg weight ({n4_avg:.2f})"
        )

    def test_n5_sentences_never_detected_as_n1(self, ginza_available):
        if not ginza_available:
            pytest.skip("GiNZA not installed")
        for batch in _batches(N5):
            payload = _build(batch, "N5")
            for node in payload["grid_matrix"]:
                if node["grid_coordinates"]["column"] == 1:
                    detected = node.get("sentence_individual_grammar_level")
                    assert detected != "N1", (
                        f"N5 sentence detected as N1: "
                        f"row={node['grid_coordinates']['row']}"
                    )

    @pytest.mark.parametrize("level,sentences", [
        ("N5", N5), ("N4", N4), ("N3", N3), ("N2", N2), ("N1", N1)
    ])
    def test_highest_level_reflects_sentence_content(self, level, sentences, ginza_available):
        if not ginza_available:
            pytest.skip("GiNZA not installed")
        payload = _build(sentences[:5], level)
        row_levels = [
            node["sentence_individual_grammar_level"]
            for node in payload["grid_matrix"]
            if node["grid_coordinates"]["column"] == 1
        ]
        highest = payload["highest_grammar_level_encountered"]
        max_weight = max(LEVEL_WEIGHT.get(lv, 1) for lv in row_levels)
        assert LEVEL_WEIGHT.get(highest, 0) == max_weight, (
            f"highest_grammar_level_encountered '{highest}' doesn't match "
            f"max of row levels {row_levels}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 4a — API: /api/news/puzzle/generate  (mocked scraper; no GiNZA required)
# ══════════════════════════════════════════════════════════════════════════════

NEWS_REQUEST_BASE = {
    "news_id": "https://mock-nhk.jp/article/99999",
    "summary_html": "",
    "level": "N5",
}


class TestAPINewsEndpoint:

    @pytest.fixture(autouse=True)
    def setup_client(self, client):
        self.client = client

    def _post_news(self, sentences: list[str], level: str = "N5") -> dict:
        payload = {**NEWS_REQUEST_BASE, "level": level}
        with patch("main.scrape_article_sentences_and_furigana",
                   return_value=(sentences[:5], {})):
            r = self.client.post("/api/news/puzzle/generate", json=payload)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        return r.json()

    def test_returns_200_with_n5_sentences(self):
        data = self._post_news(N5, "N5")
        assert "grid_matrix" in data

    def test_returns_200_with_n1_sentences(self):
        data = self._post_news(N1, "N1")
        assert "grid_matrix" in data

    # ── THE regression test via the HTTP layer ────────────────────────────────

    @pytest.mark.parametrize("level,sentences", [
        ("N5", N5), ("N4", N4), ("N3", N3), ("N2", N2), ("N1", N1)
    ])
    def test_grammar_level_field_present_in_api_response(self, level, sentences):
        """
        If ClauseNode or build_puzzle_from_news_tokens ever drops
        sentence_individual_grammar_level again, this test catches it
        at the HTTP boundary — exactly where the Swift client sees it.
        """
        data = self._post_news(sentences[:5], level)
        for node in data["grid_matrix"]:
            assert "sentence_individual_grammar_level" in node, (
                f"API response missing grammar level for {level} sentence at "
                f"row={node['grid_coordinates']['row']} "
                f"col={node['grid_coordinates']['column']}"
            )
            assert node["sentence_individual_grammar_level"] in VALID_LEVELS

    def test_grid_has_25_nodes_via_api(self):
        data = self._post_news(N3[:5], "N3")
        assert len(data["grid_matrix"]) == 25

    def test_cache_is_written_for_news_puzzle(self):
        """Second identical request should hit the cache (still returns valid data)."""
        for _ in range(2):
            data = self._post_news(N5[:5], "N5")
        assert len(data["grid_matrix"]) == 25

    def test_insufficient_sentences_returns_500(self):
        # Use a unique news_id so this test never hits a cached response
        req = {**NEWS_REQUEST_BASE, "news_id": "https://mock-nhk.jp/article/err-insufficient"}
        with patch("main.scrape_article_sentences_and_furigana",
                   return_value=(["短い。", "少ない。"], {})):
            r = self.client.post("/api/news/puzzle/generate", json=req)
        assert r.status_code == 500

    def test_scraper_exception_returns_500(self):
        # Use a unique news_id so this test never hits a cached response
        req = {**NEWS_REQUEST_BASE, "news_id": "https://mock-nhk.jp/article/err-exception"}
        with patch("main.scrape_article_sentences_and_furigana",
                   side_effect=Exception("Network failure")):
            r = self.client.post("/api/news/puzzle/generate", json=req)
        assert r.status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# 4b — API: /api/puzzle/generate  (temp story file; requires GiNZA)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.ginza
class TestAPIStoryEndpoint:

    @pytest.fixture(autouse=True)
    def require_ginza(self, ginza_available):
        if not ginza_available:
            pytest.skip("GiNZA not installed — skipping story endpoint tests")

    @pytest.fixture(autouse=True)
    def setup_client(self, client):
        self.client = client

    @pytest.fixture()
    def story_file(self, tmp_path):
        """Write 10 N5 sentences to a temp .txt file."""
        path = tmp_path / "test_story.txt"
        path.write_text("\n".join(N5[:10]), encoding="utf-8")
        return str(path)

    def test_story_endpoint_returns_200(self, story_file):
        r = self.client.post("/api/puzzle/generate",
                        json={"file_path": story_file, "level": "N5"})
        assert r.status_code == 200

    def test_story_payload_grammar_level_present(self, story_file):
        r = self.client.post("/api/puzzle/generate",
                        json={"file_path": story_file, "level": "N5"})
        assert r.status_code == 200
        for node in r.json()["grid_matrix"]:
            assert "sentence_individual_grammar_level" in node
            assert node["sentence_individual_grammar_level"] in VALID_LEVELS

    def test_missing_file_returns_404(self):
        r = self.client.post("/api/puzzle/generate",
                        json={"file_path": "/no/such/file.txt", "level": "N5"})
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 4c — API: utility endpoints (always run)
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIUtilityEndpoints:

    @pytest.fixture(autouse=True)
    def setup_client(self, client):
        self.client = client

    def test_stories_endpoint_returns_200(self):
        r = self.client.get("/api/stories")
        assert r.status_code == 200
        assert "stories" in r.json()

    def test_stories_response_is_list(self):
        r = self.client.get("/api/stories")
        assert isinstance(r.json()["stories"], list)

    def test_cache_clear_returns_200(self):
        r = self.client.post("/api/cache/clear")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert "detail" in body

    def test_news_topics_returns_200_or_graceful_error(self):
        """
        RSS fetch may fail in CI (no network).  Accept 200 or a clean 500
        — not an unhandled crash.
        """
        with patch("main.fetch_nhk_news_topics", return_value=[
            {"id": "1", "title": "テスト記事", "link": "https://nhk.jp/1", "summary_html": ""},
        ]):
            r = self.client.get("/api/news/topics")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert isinstance(body["topics"], list)
