from datetime import date

from app.core.config import get_settings

TODAY = date.today()
D = TODAY.isoformat()


def upload(client, auth, account, content: bytes | str, filename="tx.csv", **form):
    if isinstance(content, str):
        content = content.encode()
    return client.post("/api/v1/transactions/import", headers=auth, files={"file": (filename, content, "text/csv")},
                       data={"account_id": account["id"], **form})


def test_basic_import_categorizes_and_summarizes(client, auth, account):
    csv = (f"Date,Description,Amount,Extra\n{D},STARBUCKS #123,-5.50,x\n{D},Payroll ACME Inc,3000,y\n"
           f"{D},Unknown Shop 99,-20,z\n")
    r = upload(client, auth, account, csv)
    assert r.status_code == 200, r.text
    s = r.json()
    assert (s["total_rows"], s["imported"], s["duplicates"], s["rejected"]) == (3, 3, 0, 0)
    assert s["categorized"] == 2 and s["uncategorized"] == 1 and s["ignored_columns"] == ["Extra"]
    items = client.get("/api/v1/transactions", headers=auth).json()["items"]
    by_desc = {t["description"]: t for t in items}
    assert by_desc["STARBUCKS #123"]["category_name"] == "Food" and by_desc["STARBUCKS #123"]["direction"] == "expense"
    assert by_desc["Payroll ACME Inc"]["category_name"] == "Salary" and by_desc["Payroll ACME Inc"]["direction"] == "income"
    assert by_desc["Unknown Shop 99"]["category_name"] is None


def test_reimport_is_idempotent_but_same_day_twins_inside_one_file_are_kept(client, auth, account):
    csv = f"date,description,amount\n{D},Coffee Shop,-4\n{D},Coffee Shop,-4\n"
    first = upload(client, auth, account, csv).json()
    assert first["imported"] == 2  # two identical coffees on one day are legitimate
    again = upload(client, auth, account, csv).json()
    assert again["imported"] == 0 and again["duplicates"] == 2
    assert client.get("/api/v1/transactions", headers=auth).json()["total"] == 2


def test_overlapping_file_only_adds_new_rows(client, auth, account):
    upload(client, auth, account, f"date,description,amount\n{D},A shop,-1\n")
    r = upload(client, auth, account, f"date,description,amount\n{D},A shop,-1\n{D},B shop,-2\n").json()
    assert r["imported"] == 1 and r["duplicates"] == 1


def test_bad_rows_are_rejected_individually(client, auth, account):
    csv = ("date,description,amount\n"
           f"{D},ok row,-1\nnot-a-date,bad date,-1\n{D},bad amount,abc\n{D},zero,0\n{D},too,many,fields,-1\n"
           f"2999-01-01,future,-5\n,,\n")
    s = upload(client, auth, account, csv).json()
    assert s["imported"] == 1 and s["rejected"] == 5
    assert {e["row"] for e in s["errors"]} == {3, 4, 5, 6, 7}


def test_missing_description_gets_placeholder(client, auth, account):
    s = upload(client, auth, account, f"date,description,amount\n{D},,-9\n").json()
    assert s["imported"] == 1
    assert client.get("/api/v1/transactions", headers=auth).json()["items"][0]["description"] == "(no description)"


def test_debit_credit_columns_and_semicolon_delimiter(client, auth, account):
    csv = f"Posted;Memo;Debit;Credit\n{D};Shell fuel;40,25;\n{D};Payroll;;1.500,00\n"
    s = upload(client, auth, account, csv).json()
    assert s["imported"] == 2, s
    items = {t["description"]: t for t in client.get("/api/v1/transactions", headers=auth).json()["items"]}
    assert items["Shell fuel"]["amount"] == "40.25" and items["Shell fuel"]["direction"] == "expense"
    assert items["Payroll"]["amount"] == "1500.00" and items["Payroll"]["direction"] == "income"


def test_inverted_convention_for_credit_card_statements(client, auth, account):
    s = upload(client, auth, account, f"date,description,amount\n{D},Netflix,15.99\n{D},Payment thanks,-200\n",
               amount_convention="inverted").json()
    items = {t["description"]: t for t in client.get("/api/v1/transactions", headers=auth).json()["items"]}
    assert items["Netflix"]["direction"] == "expense" and items["Payment thanks"]["direction"] == "income"


def test_type_column_and_parentheses_and_currency_symbols(client, auth, account):
    csv = f"date,description,amount,type\n{D},Gym,$25.00,debit\n{D},Cashback,($3.00),credit\n"
    upload(client, auth, account, csv)
    items = {t["description"]: t for t in client.get("/api/v1/transactions", headers=auth).json()["items"]}
    assert items["Gym"]["direction"] == "expense" and items["Gym"]["amount"] == "25.00"
    assert items["Cashback"]["direction"] == "income" and items["Cashback"]["amount"] == "3.00"


def test_currency_mismatch_row_rejected(client, auth, account):
    s = upload(client, auth, account, f"date,description,amount,currency\n{D},Hotel,-50,EUR\n{D},Taxi,-5,USD\n").json()
    assert s["imported"] == 1 and "does not match" in s["errors"][0]["error"]


def test_latin1_encoding_is_handled(client, auth, account):
    csv = f"date,description,amount\n{D},Café Zürich,-7\n".encode("cp1252")
    assert upload(client, auth, account, csv).json()["imported"] == 1
    assert "Caf" in client.get("/api/v1/transactions", headers=auth).json()["items"][0]["description"]


def test_missing_required_columns(client, auth, account):
    r = upload(client, auth, account, "foo,bar\n1,2\n")
    assert r.status_code == 422 and r.json()["error"]["code"] == "MISSING_COLUMNS"


def test_empty_and_header_only_files(client, auth, account):
    assert upload(client, auth, account, "").json()["error"]["code"] == "EMPTY_FILE"
    assert upload(client, auth, account, "date,description,amount\n").json()["error"]["code"] == "EMPTY_FILE"


def test_invalid_type_binary_and_oversize(client, auth, account):
    assert upload(client, auth, account, "a,b", filename="x.txt").json()["error"]["code"] == "INVALID_FILE_TYPE"
    assert upload(client, auth, account, b"\x00\x01\x02binary", filename="x.csv").json()["error"]["code"] == "INVALID_FILE_TYPE"
    s = get_settings()
    old = s.max_upload_mb
    s.max_upload_mb = 1
    try:
        big = b"date,description,amount\n" + (f"{D},Shop,-1\n".encode() * 150_000)
        r = upload(client, auth, account, big)
        assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    finally:
        s.max_upload_mb = old


def test_row_limit(client, auth, account):
    s = get_settings()
    old = s.max_import_rows
    s.max_import_rows = 3
    try:
        csv = "date,description,amount\n" + "".join(f"{D},Shop {i},-1\n" for i in range(5))
        assert upload(client, auth, account, csv).json()["error"]["code"] == "TOO_MANY_ROWS"
    finally:
        s.max_import_rows = old


def test_import_into_someone_elses_account_is_404(client, auth, auth_b, account):
    r = upload(client, auth_b, account, f"date,description,amount\n{D},x,-1\n")
    assert r.status_code == 404 and r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_formula_like_and_script_descriptions_stored_as_text(client, auth, account):
    csv = f'date,description,amount\n{D},"=HYPERLINK(""http://evil"")<script>alert(1)</script>",-1\n'
    assert upload(client, auth, account, csv).json()["imported"] == 1


def test_import_flags_unusual_transaction(client, auth, account):
    rows = "".join(f"{D},Local Cafe,-{20 + i}\n" for i in range(8))
    csv = "date,description,amount\n" + rows + f"{D},Local Cafe,-480\n"
    s = upload(client, auth, account, csv).json()
    assert s["anomalies_flagged"] == 1
    alerts = client.get("/api/v1/alerts", headers=auth).json()
    assert alerts["total"] == 1 and alerts["items"][0]["type"] == "UNUSUAL_TRANSACTION"
    assert "not a fraud determination" in alerts["items"][0]["message"]
