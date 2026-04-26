@echo off
chcp 65001 >nul
set BASE_URL=https://playto-pay-engine.onrender.com

echo ==========================================================
echo   PLAYTO PAYOUT ENGINE - TEST SUITE
echo ==========================================================
echo.

REM ============================================================================
REM TEST 1: Basic Payout Creation
echo [TEST 1] Creating a basic payout of INR 50 from Acme Agency...
curl -s -X POST %BASE_URL%/api/v1/payouts/ -H "Authorization: Api-Key api-key-acme-agency" -H "Content-Type: application/json" -H "Idempotency-Key: 11111111-1111-1111-1111-111111111111" -d "{\"amount_paise\": 5000, \"bank_account_id\": \"basic-test\"}" > test1.json
findstr "id" test1.json >nul
if %errorlevel% == 0 (
    echo          PASS: Payout created.
) else (
    echo          FAIL: Payout creation failed.
)
echo Response:
type test1.json
echo.

REM ============================================================================
REM TEST 2: Idempotency - Same key, same result
echo [TEST 2] Testing idempotency (same key twice)...
set KEY=22222222-2222-2222-2222-222222222222

curl -s -X POST %BASE_URL%/api/v1/payouts/ -H "Authorization: Api-Key api-key-freelancer-fiaz" -H "Content-Type: application/json" -H "Idempotency-Key: %KEY%" -d "{\"amount_paise\": 1000, \"bank_account_id\": \"idempotency-test\"}" > test2a.json
curl -s -X POST %BASE_URL%/api/v1/payouts/ -H "Authorization: Api-Key api-key-freelancer-fiaz" -H "Content-Type: application/json" -H "Idempotency-Key: %KEY%" -d "{\"amount_paise\": 1000, \"bank_account_id\": \"idempotency-test\"}" > test2b.json

echo First request:
type test2a.json
echo.
echo Second request (same key):
type test2b.json
echo.
echo          Check: Both should show the SAME payout ID.
echo.

REM ============================================================================
REM TEST 3: Concurrency - Prevent overdraft
echo [TEST 3] Testing concurrency - Two INR 60 payouts against INR 100 balance...
echo          Preparing concurrent requests...

REM Write curl commands to temp batch files so quotes are preserved
echo curl -s -X POST %BASE_URL%/api/v1/payouts/ -H "Authorization: Api-Key api-key-tiny-studio" -H "Content-Type: application/json" -H "Idempotency-Key: 33333333-3333-3333-3333-333333333333" -d "{\"amount_paise\": 6000, \"bank_account_id\": \"concurrency-a\"}" ^> test3a.json > _req_a.bat
echo curl -s -X POST %BASE_URL%/api/v1/payouts/ -H "Authorization: Api-Key api-key-tiny-studio" -H "Content-Type: application/json" -H "Idempotency-Key: 44444444-4444-4444-4444-444444444444" -d "{\"amount_paise\": 6000, \"bank_account_id\": \"concurrency-b\"}" ^> test3b.json > _req_b.bat

echo          Firing Request A...
start /b _req_a.bat
echo          Firing Request B...
start /b _req_b.bat

echo          Waiting 5 seconds...
ping -n 6 127.0.0.1 >nul

echo Request A result:
type test3a.json
echo.
echo Request B result:
type test3b.json
echo.
echo          Check: Exactly one should be 201, the other 400 (insufficient balance).
echo.

REM ============================================================================
REM TEST 4: Ledger Invariant
echo [TEST 4] Checking ledger invariant for Acme Agency...
curl -s %BASE_URL%/api/v1/me/ -H "Authorization: Api-Key api-key-acme-agency" > test4_me.json
curl -s %BASE_URL%/api/v1/ledger/ -H "Authorization: Api-Key api-key-acme-agency" > test4_ledger.json

echo Merchant profile (available_balance_paise should equal sum(credits) - sum(debits)):
type test4_me.json
echo.
echo Ledger entries:
type test4_ledger.json
echo.

REM ============================================================================
REM CLEANUP
del test1.json test2a.json test2b.json test3a.json test3b.json test4_me.json test4_ledger.json _req_a.bat _req_b.bat 2>nul

echo ==========================================================
echo   TESTS COMPLETE
echo ==========================================================
echo.
pause
