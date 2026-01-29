import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";

// ✅ 여기에 네 Supabase 값 넣기 (프론트 공개용)
const SUPABASE_URL = "https://ceyqzzxxnsrntjiwnxuj.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_Tr9xESxeyZWmOEFVpNsS1g_zP7mMecP";

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const memoInput = document.getElementById("memoInput");
const addBtn = document.getElementById("addBtn");
const refreshBtn = document.getElementById("refreshBtn");
const memoList = document.getElementById("memoList");
const statusEl = document.getElementById("status");

function setStatus(msg) {
  statusEl.textContent = `상태: ${msg}`;
}

function renderMemos(rows) {
  memoList.innerHTML = "";
  for (const r of rows) {
    const li = document.createElement("li");
    const t = new Date(r.createdAt).toLocaleString();
    li.textContent = `${r.text}  `;
    const span = document.createElement("span");
    span.className = "meta";
    span.textContent = `(${t})`;
    li.appendChild(span);
    memoList.appendChild(li);
  }
}

async function readMemos() {
  setStatus("DB에서 목록 읽는 중...");
  const { data, error } = await supabase
    .from("memos")
    .select("id,text,createdAt")
    .order("createdAt", { ascending: false })
    .limit(30);

  if (error) {
    console.error(error);
    setStatus(`읽기 실패: ${error.message}`);
    return;
  }
  renderMemos(data ?? []);
  setStatus(`읽기 완료 (총 ${data?.length ?? 0}개)`);
}

async function createMemo(text) {
  setStatus("DB에 저장 중...");
  const { error } = await supabase
    .from("memos")
    .insert([{ text }]);

  if (error) {
    console.error(error);
    setStatus(`저장 실패: ${error.message}`);
    return false;
  }
  setStatus("저장 완료");
  return true;
}

addBtn.addEventListener("click", async () => {
  const text = memoInput.value.trim();
  if (!text) {
    setStatus("메모를 입력하세요.");
    return;
  }
  const ok = await createMemo(text);
  if (ok) {
    memoInput.value = "";
    await readMemos();
  }
});

refreshBtn.addEventListener("click", async () => {
  await readMemos();
});

// 첫 로드 시 목록 읽기
readMemos();
