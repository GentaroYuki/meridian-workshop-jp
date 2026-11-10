# API テスト

工場在庫管理システムのバックエンド API を対象とした包括的なテストスイートです。

## テストの構成

```
tests/
├── pytest.ini          # Pytest configuration
├── backend/            # Backend API tests
│   ├── conftest.py     # Test fixtures and configuration
│   ├── test_inventory.py        # Inventory endpoint tests (10 tests)
│   ├── test_orders.py           # Orders endpoint tests (21 tests, 2 xfail)
│   ├── test_purchase_orders.py  # Purchase order endpoint tests (14 tests)
│   ├── test_dashboard.py        # Dashboard endpoint tests (13 tests)
│   └── test_misc_endpoints.py   # Demand, backlog, spending, root tests (18 tests)
├── TEST_SUMMARY.md     # Test summary
└── README.md           # This file
```

## テストの実行方法

### すべてのテストを実行する
```bash
cd tests
uv run --project ../server pytest -v
```

### 特定のテストファイルを実行する
```bash
cd tests
uv run --project ../server pytest backend/test_inventory.py -v
```

### 特定のテストクラスを実行する
```bash
cd tests
uv run --project ../server pytest backend/test_inventory.py::TestInventoryEndpoints -v
```

### 特定のテストだけを実行する
```bash
cd tests
uv run --project ../server pytest backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory -v
```

### カバレッジ付きで実行する(pytest-cov が必要)
```bash
cd tests
uv run --project ../server pytest --cov=../server --cov-report=html
```

## テストカバレッジ

**合計 76 テスト**(74 件成功、2 件は既知のデータ不整合による xfail)です。Reports(`/api/reports/*`)の endpoint には専用のテストがありません。

### 在庫関連の endpoint(10 テスト)
- ✓ 全在庫アイテムの取得
- ✓ 倉庫によるフィルタリング
- ✓ カテゴリによるフィルタリング(Power Supplies を含む)
- ✓ 複数条件でのフィルタリング
- ✓ ID を指定した特定アイテムの取得
- ✓ 存在しないアイテムの処理(404)
- ✓ フィールド構造の検証
- ✓ データ型の検証

### 注文関連の endpoint(21 テスト)
- ✓ 全注文の取得、フィールド・注文アイテムの構造、ステータス値、日付フォーマット(ISO)
- ✓ 合計金額 = sum(数量 × 単価) の検算
- ✓ 配達済み以外の注文に actual_delivery がないこと
- ✓ 倉庫、カテゴリ(大文字小文字を区別しない)、ステータス、月、四半期によるフィルタリング
- ✓ 四半期 Q1〜Q4 で全注文が重複なく分かれること、`all` の扱い、複数フィルターの組み合わせ、該当なしで空配列
- ✓ ID を指定した取得、存在しない注文の 404
- ✗(xfail)配達済みの注文すべてに actual_delivery があること: 8 件で欠落しています
- ✗(xfail)注文 ID が一意であること: ID 201〜210 が 2 件ずつあります

### 発注関連の endpoint(14 テスト)
- ✓ `POST /api/purchase-orders` で発注を作成(201)、作成した発注を `GET /api/purchase-orders/{backlog_item_id}` で取得
- ✓ 作成後に `/api/backlog` の has_purchase_order が true になること
- ✓ 同じバックログに 2 件目は 409、存在しないバックログは 404、空白だけの仕入先は 400
- ✓ 数量 0 以下・負の単価・空の仕入先・不正な日付は 422 で、何も作成されないこと
- ✓ 発注がないバックログの取得は 404

### ダッシュボード関連の endpoint(13 テスト)
- ✓ ダッシュボードサマリーの取得
- ✓ データ型と非負値の検証
- ✓ 倉庫、カテゴリ、ステータス、月によるフィルタリング
- ✓ 複数フィルターの組み合わせ
- ✓ 計算精度の検証:
  - 保留中注文数の計算
  - 在庫僅少アイテム数の計算
  - 在庫総額の計算

### その他の endpoint(18 テスト)
- **需要予測(6 テスト)**
  - ✓ 需要予測の取得
  - ✓ トレンド値の検証
  - ✓ 非負値の検証
  - ✓ stable の変化率が increasing / decreasing より小さいこと
  - ✓ トレンドと予測値の増減の向きの一致
  - ✓ SKU と品名が在庫データと一致すること

- **バックログアイテム(4 テスト)**
  - ✓ バックログアイテムの取得
  - ✓ 優先度の値の検証
  - ✓ 数量ロジックの検証
  - ✓ 遅延日数の検証

- **支出データ(6 テスト)**
  - ✓ 支出サマリーの取得
  - ✓ 月次支出の取得
  - ✓ 月次支出にすべてのコストカテゴリが揃っていること
  - ✓ 月次支出にばらつきがあること
  - ✓ カテゴリ別支出の取得
  - ✓ 直近の取引履歴の取得

- **ルート endpoint(2 テスト)**
  - ✓ API 情報 endpoint
  - ✓ レスポンス構造の検証

## テストの特徴

- **FastAPI TestClient**: FastAPI 組み込みのテストクライアントを使った、高速で独立性の高いテストです
- **Fixture**: 再利用可能な fixture を `conftest.py` にまとめています
- **包括的な検証**: データ構造、型、計算結果、ビジネスロジックまで確認します
- **フィルターのテスト**: すべてのフィルターの組み合わせとエッジケースを検証します
- **エラーハンドリング**: 404 レスポンスやエッジケースもテストします
- **新機能への対応**: Power Supplies カテゴリのテストも含まれています

## 依存パッケージ

テストの実行には以下のパッケージが必要です(`server/` の開発用依存です。`cd server && uv sync` でインストールされます)。
- pytest >= 8.0.0
- pytest-asyncio >= 0.23.0
- httpx >= 0.27.0
- pytest-cov >= 4.1.0(任意。カバレッジレポート用)

## 新しいテストの追加

1. `tests/backend/` に `test_*.py` という命名規則でテストファイルを作成します
2. conftest.py の `client` fixture を利用します
3. テストクラスを作成します(必須ではありませんが、整理のため推奨します)
4. `test_` で始まるテスト関数を書きます
5. テストを実行して動作を確認します

例:
```python
class TestNewEndpoint:
    def test_new_feature(self, client):
        response = client.get("/api/new-endpoint")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

## CI/CD との連携

CI/CD パイプラインに組み込む場合の例です。

```yaml
# Example GitHub Actions
- name: Run API Tests
  run: |
    cd tests
    uv run --project ../server pytest -v --tb=short
```

## 補足

- すべてのテストはインメモリの mock データを使用します(データベースは不要です)
- 各テストは独立しており、任意の順序で実行できます
- アプリのライフサイクルは FastAPI TestClient が自動的に管理します
- テストは約 0.13 秒で完了します
