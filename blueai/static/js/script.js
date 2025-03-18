document.addEventListener("DOMContentLoaded", function () {
  // DOM 요소
  const sidebar = document.getElementById("sidebar");
  const sidebarTrigger = document.getElementById("sidebarTrigger");
  const logoIcon = document.getElementById("logoIcon");
  const sidebarPin = document.getElementById("sidebarPin");
  const main = document.getElementById("main");
  const taskTitle = document.getElementById("taskTitle");
  const titleDropdown = document.querySelector(".title-dropdown");
  const fileUploadBtn = document.getElementById("fileUploadBtn");
  const fileUpload = document.getElementById("fileUpload");
  const mainFileUploadBtn = document.getElementById("mainFileUploadBtn");
  const mainFileUpload = document.getElementById("mainFileUpload");
  const userInput = document.getElementById("userInput");
  const enterBtn = document.getElementById("enterBtn");
  const utilityButtons = document.querySelectorAll(".utility-button");
  const chatWindow = document.getElementById("chatWindow");
  const taskList = document.getElementById("taskList");
  const favoritesList = document.getElementById("favoritesList");
  const newChatBtn = document.getElementById("newChat");
  const welcomePage = document.getElementById("welcomePage");
  const chatPage = document.getElementById("chatPage");
  const mainInput = document.getElementById("mainInput");
  const mainEnterBtn = document.getElementById("mainEnterBtn");
  const exampleCards = document.querySelectorAll(".example-card");
  const tabButtons = document.querySelectorAll(".tab-button");
  const viewAllTasks = document.getElementById("viewAllTasks");
  const allTasksModal = document.getElementById("allTasksModal");
  const logDiaryBtn = document.getElementById("logDiaryBtn");
  const shareBtn = document.getElementById("shareBtn");
  const favoriteBtn = document.getElementById("favoriteBtn");
  const logDiaryPanel = document.getElementById("logDiaryPanel");
  const closeLogDiaryBtn = document.querySelector(".close-panel");
  const sendIcons = document.querySelectorAll(".send-icon");
  const micIcons = document.querySelectorAll(".mic-icon");
  const userBtn = document.getElementById("userBtn");
  const quickActionBtns = document.querySelectorAll(".quick-action-btn");
  const footerButtons = document.querySelectorAll(".footer-button");

  // 모델, 모드, 스타일 선택 UI 요소
  const modelButtons = document.querySelectorAll(".model-button");
  const modelDropdowns = document.querySelectorAll(".model-dropdown");
  const modelOptions = document.querySelectorAll(".model-option");

  const styleButtons = document.querySelectorAll(".style-button");
  const styleDropdowns = document.querySelectorAll(".style-dropdown");
  const styleOptions = document.querySelectorAll(".style-option");

  const renameButton = document.querySelector(".dropdown-item.rename");
  const deleteButton = document.querySelector(".dropdown-item.delete");

  // CSRF 토큰 가져오기 함수
  function getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
  }

  // 현재 활성화된 작업 ID와 대화 기록
  let currentTaskId = null;
  let currentConversation = [];
  let favoriteTaskIds = [];
  let isListening = false;

  // 드롭다운 상태 관리 (토글 대상)
  let activeDropdown = null;

  // 작업 데이터 저장소
  const taskData = {};

  // 로컬 스토리지에서 작업 데이터 불러오기
  const loadLocalData = () => {
    const storedData = localStorage.getItem("blueai_tasks");
    if (storedData) {
      const parsed = JSON.parse(storedData);
      Object.assign(taskData, parsed);
    }

    const storedFavorites = localStorage.getItem("blueai_favorites");
    if (storedFavorites) {
      favoriteTaskIds = JSON.parse(storedFavorites);
    }
  };

  // 로컬 스토리지에 작업 데이터 저장
  const saveLocalData = () => {
    localStorage.setItem("blueai_tasks", JSON.stringify(taskData));
    localStorage.setItem("blueai_favorites", JSON.stringify(favoriteTaskIds));
  };

  // localStorage를 이용한 대화 상태 저장 함수
  function saveConversationState() {
    if (
      currentTaskId &&
      currentConversation &&
      currentConversation.length > 0
    ) {
      const state = {
        taskId: currentTaskId,
        conversation: currentConversation,
        timestamp: new Date().getTime(),
      };
      localStorage.setItem(
        "blueai_current_conversation",
        JSON.stringify(state)
      );
      console.log("Conversation state saved:", state);
    }
  }

  // 상태 복원 함수
  function restoreConversationState() {
    const saved = localStorage.getItem("blueai_current_conversation");
    if (saved) {
      try {
        const state = JSON.parse(saved);

        // 1시간 이내 데이터만 복원 (선택적)
        const now = new Date().getTime();
        const oneHour = 60 * 60 * 1000;

        if (
          state.taskId &&
          state.conversation &&
          now - state.timestamp < oneHour
        ) {
          console.log("Restoring conversation:", state);
          // 서버에서 작업 상세 정보 로드
          loadTask(state.taskId);
          return true;
        }
      } catch (e) {
        console.error("Error restoring conversation:", e);
      }
    }
    return false;
  }

  // 사이드바 타이머 및 상태
  let sidebarTimer = null;

  // 페이지 로드 시 초기화
  loadLocalData();
  loadTasks();
  loadFavorites();

  // 로그인 상태 확인 및 UI 업데이트
  function updateUIBasedOnAuthStatus() {
    // window.isAuthenticated 변수는 템플릿에서 설정됨
    const isAuthenticated = window.isAuthenticated === true;

    // 로그인 상태에 따라 UI 요소 표시/숨김
    if (isAuthenticated) {
      // 로그인된 사용자 UI
      if (document.querySelector(".auth-buttons")) {
        document.querySelector(".auth-buttons").style.display = "none";
      }

      if (document.querySelector(".login-buttons")) {
        document.querySelector(".login-buttons").style.display = "none";
      }

      // 작업 관련 UI 활성화
      if (newChatBtn) newChatBtn.style.display = "block";
      if (taskList) taskList.style.display = "block";
    } else {
      // 비로그인 사용자 UI
      if (document.querySelector(".auth-buttons")) {
        document.querySelector(".auth-buttons").style.display = "flex";
      }

      // 로그인 버튼 표시
      if (document.querySelector(".login-buttons")) {
        document.querySelector(".login-buttons").style.display = "flex";
      }
    }
  }

  // 사용자 정보 표시 함수
  function updateUserDisplay() {
    const userBtn = document.getElementById("userBtn");
    const userNameText = document.querySelector(".user-name-text");

    // 서버에서 전달된 사용자 데이터가 있는지 확인
    if (window.userDisplayName) {
      if (userNameText) {
        userNameText.textContent = window.userDisplayName;
      }

      if (userBtn && window.userInitial) {
        userBtn.textContent = window.userInitial;
      }
    }
  }

  // 페이지 로드 시 실행
  updateUIBasedOnAuthStatus();
  updateUserDisplay();

  // 페이지 종료 전 상태 저장
  window.addEventListener("beforeunload", function () {
    saveConversationState();
  });

  // 메인 입력창 텍스트 영역 자동 높이 조절 - ChatGPT 스타일로 개선
  mainInput.addEventListener("input", function () {
    // 기존 아이콘 변경 로직 유지
    if (this.value.trim()) {
      mainEnterBtn.querySelector(".send-icon").style.display = "inline-block";
      mainEnterBtn.querySelector(".mic-icon").style.display = "none";
    } else if (!isListening) {
      mainEnterBtn.querySelector(".send-icon").style.display = "none";
      mainEnterBtn.querySelector(".mic-icon").style.display = "inline-block";
    }

    // 메인 입력창 높이 자동 조절 추가
    adjustTextareaHeight(this);
  });

  document.querySelectorAll(".lang-dropdown .dropdown-link").forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      // 같은 드롭다운 내 모든 링크에서 active 클래스 제거
      document
        .querySelectorAll(".lang-dropdown .dropdown-link")
        .forEach((l) => {
          l.classList.remove("active");
          const checkIcon = l.querySelector(".check-icon");
          if (checkIcon) {
            checkIcon.style.display = "none";
          }
        });

      // 현재 링크에 active 클래스 추가
      this.classList.add("active");

      // 체크 아이콘 표시
      const checkIcon = this.querySelector(".check-icon");
      if (checkIcon) {
        checkIcon.style.display = "inline-block";
      }
    });
  });

  // 서브페이지 입력창 높이 자동 조절
  userInput.addEventListener("input", function () {
    // 기존 아이콘 변경 로직 유지
    if (this.value.trim()) {
      enterBtn.querySelector(".send-icon").style.display = "inline-block";
      enterBtn.querySelector(".mic-icon").style.display = "none";
    } else if (!isListening) {
      enterBtn.querySelector(".send-icon").style.display = "none";
      enterBtn.querySelector(".mic-icon").style.display = "inline-block";
    }

    // 입력창 높이 자동 조절
    adjustTextareaHeight(this);
  });

  // 텍스트 영역 높이 자동 조절 함수 (ChatGPT 스타일)
  function adjustTextareaHeight(textarea) {
    textarea.style.height = "auto";

    // 내용 높이에 따라 높이 설정 (최소/최대 높이 제한)
    const minHeight = 24;
    const maxHeight = 150;
    const newHeight = Math.min(
      Math.max(textarea.scrollHeight, minHeight),
      maxHeight
    );
    textarea.style.height = newHeight + "px";

    // 스크롤바 표시 여부 설정
    textarea.style.overflowY = newHeight >= maxHeight ? "auto" : "hidden";

    // 부모 컨테이너의 패딩 고려하여 전송 버튼 위치 조정
    const container = textarea.closest(
      ".main-input-container, .input-flex-container"
    );
    if (container) {
      const sendButton = container.querySelector(
        ".main-enter-btn, .send-button"
      );
      if (sendButton) {
        const bottomPosition = Math.min(15 + (newHeight - minHeight) / 3, 40);
        sendButton.style.bottom = bottomPosition + "px";
      }
    }
  }

  // 파일 업로드 이벤트
  mainFileUploadBtn.addEventListener("click", function () {
    mainFileUpload.click();
  });

  mainFileUpload.addEventListener("change", function (event) {
    const files = event.target.files;
    if (files.length > 0) {
      mainInput.value += ` [파일: ${files[0].name}]`;
      mainInput.dispatchEvent(new Event("input"));
    }
  });

  // 메인 입력창 특수 키 처리 - Shift+Enter만 줄바꿈, 나머지는 전송
  mainInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      if (event.shiftKey) {
        // Shift+Enter는 줄바꿈 추가
        const cursorPos = this.selectionStart;
        const textBefore = this.value.substring(0, cursorPos);
        const textAfter = this.value.substring(cursorPos);

        this.value = textBefore + "\n" + textAfter;
        this.selectionStart = this.selectionEnd = cursorPos + 1;

        // 높이 조정 트리거
        adjustTextareaHeight(this);
        event.preventDefault();
      } else {
        // 일반 Enter, Ctrl+Enter, Alt+Enter는 모두 명령어 전송
        event.preventDefault();
        processMainInput();
      }
    }
  });

  // 서브페이지 입력창 특수 키 처리
  userInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      if (event.shiftKey) {
        // Shift+Enter는 줄바꿈 추가
        const cursorPos = this.selectionStart;
        const textBefore = this.value.substring(0, cursorPos);
        const textAfter = this.value.substring(cursorPos);

        this.value = textBefore + "\n" + textAfter;
        this.selectionStart = this.selectionEnd = cursorPos + 1;

        // 높이 조정 트리거
        adjustTextareaHeight(this);
        event.preventDefault();
      } else {
        // 일반 Enter는 명령어 전송
        event.preventDefault();
        processCommand();
      }
    }
  });

  // B 로고 호버 이벤트 (마우스 스크립트)
  sidebarTrigger.addEventListener("mouseenter", function () {
    // 사이드바 표시
    clearTimeout(sidebarTimer);
    sidebar.classList.remove("hover-delay");
    sidebar.classList.remove("collapsed");
    main.classList.remove("sidebar-collapsed");

    // 로고 확장 효과만 유지하고 글자 겹침 문제 해결
    const logo = this.querySelector(".logo-icon");
    if (logo) {
      logo.textContent = "B"; // B만 표시하여 텍스트 겹침 방지
    }
  });

  // B 로고 클릭 이벤트 - 웰컴 페이지로 이동
  sidebarTrigger.addEventListener("click", function () {
    // 웰컴 페이지 표시 (사이드바 토글 대신)
    welcomePage.style.display = "flex";
    chatPage.style.display = "none";

    // 헤더 중앙의 작업 제목 숨기기
    taskTitle.style.display = "none";

    // 현재 작업 초기화
    currentTaskId = null;
    currentConversation = [];

    // 입력창 초기화
    mainInput.value = "";
    mainInput.dispatchEvent(new Event("input"));
    mainInput.focus();

    // 헤더 버튼 가시성 업데이트
    updateHeaderButtonsVisibility();
  });

  // 사이드바 호버 기능 개선
  sidebar.addEventListener("mouseenter", function () {
    clearTimeout(sidebarTimer); // 기존 타이머 제거
    if (
      sidebar.classList.contains("collapsed") &&
      !sidebar.classList.contains("pinned")
    ) {
      sidebar.classList.remove("hover-delay"); // 딜레이 제거
      sidebar.classList.remove("collapsed");
      main.classList.remove("sidebar-collapsed");
    }
  });

  // 사이드바 닫힘 딜레이 처리
  sidebar.addEventListener("mouseleave", function () {
    if (
      !sidebar.classList.contains("collapsed") &&
      !sidebar.classList.contains("pinned")
    ) {
      clearTimeout(sidebarTimer); // 기존 타이머 제거
      sidebar.classList.add("hover-delay"); // 딜레이 추가
      sidebarTimer = setTimeout(() => {
        sidebar.classList.add("collapsed");
        main.classList.add("sidebar-collapsed");
        sidebar.classList.remove("hover-delay"); // 딜레이 제거
      }, 400); // 마우스가 떠난 후 400ms 후에 사이드바 닫힘
    }
  });

  // 사이드바 핀 버튼 클릭 이벤트
  sidebarPin.addEventListener("click", function () {
    this.classList.toggle("active");
    sidebar.classList.toggle("pinned");

    // 툴팁 텍스트 변경
    const tooltip = this.querySelector(".pin-tooltip");
    if (this.classList.contains("active")) {
      tooltip.textContent = "사이드바 고정 해제";
    } else {
      tooltip.textContent = "사이드바 고정";
    }
  });

  // 모든 활성 드롭다운 닫기
  function closeAllDropdowns() {
    const dropdowns = document.querySelectorAll(
      ".title-dropdown.show, .user-dropdown.show, .footer-dropdown.show, .model-dropdown.show, .style-dropdown.show"
    );
    dropdowns.forEach((dropdown) => {
      dropdown.classList.remove("show");
    });
    activeDropdown = null;
  }

  // 문서 클릭 시 모든 드롭다운 닫기
  document.addEventListener("click", function (e) {
    const isDropdownTrigger = e.target.closest(
      ".task-title, .user-button, .footer-button, .model-button, .style-button, .header-title"
    );
    const isDropdown = e.target.closest(
      ".title-dropdown, .user-dropdown, .footer-dropdown, .model-dropdown, .style-dropdown"
    );

    if (!isDropdownTrigger && !isDropdown) {
      closeAllDropdowns();
    }
  });

  // 제목 클릭 시 드롭다운 토글 - 이름 변경/삭제 메뉴
  if (taskTitle) {
    taskTitle.addEventListener("click", function (e) {
      e.stopPropagation();
      e.preventDefault();

      // 다른 활성 드롭다운 닫기
      document
        .querySelectorAll(
          ".user-dropdown.show, .footer-dropdown.show, .model-dropdown.show, .style-dropdown.show"
        )
        .forEach((dropdown) => {
          dropdown.classList.remove("show");
        });

      // 현재 드롭다운 토글
      if (titleDropdown) {
        titleDropdown.classList.toggle("show");

        if (titleDropdown.classList.contains("show")) {
          activeDropdown = titleDropdown;
        } else {
          activeDropdown = null;
        }
      }
    });
  }

  // 사용자 버튼 클릭 시 드롭다운 토글
  if (userBtn) {
    userBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      const dropdown = document.querySelector(".user-dropdown");

      // 다른 활성 드롭다운 닫기
      document
        .querySelectorAll(
          ".title-dropdown.show, .footer-dropdown.show, .model-dropdown.show, .style-dropdown.show"
        )
        .forEach((dropdown) => {
          dropdown.classList.remove("show");
        });

      // 현재 드롭다운 토글
      if (dropdown) {
        dropdown.classList.toggle("show");

        if (dropdown.classList.contains("show")) {
          activeDropdown = dropdown;
        } else {
          activeDropdown = null;
        }
      }
    });
  }

  // 모델 선택 기능 - 모든 모델 버튼에 적용
  modelButtons.forEach((modelButton, index) => {
    const modelDropdown = modelDropdowns[index];

    if (modelButton && modelDropdown) {
      modelButton.addEventListener("click", function (e) {
        e.stopPropagation();

        // 다른 드롭다운 닫기
        document
          .querySelectorAll(
            ".title-dropdown.show, .user-dropdown.show, .footer-dropdown.show, .style-dropdown.show"
          )
          .forEach((dropdown) => {
            dropdown.classList.remove("show");
          });

        // 다른 모델 드롭다운도 닫기
        modelDropdowns.forEach((dropdown) => {
          if (dropdown !== modelDropdown) {
            dropdown.classList.remove("show");
          }
        });

        modelDropdown.classList.toggle("show");

        if (modelDropdown.classList.contains("show")) {
          activeDropdown = modelDropdown;
        } else {
          activeDropdown = null;
        }
      });
    }
  });

  // 푸터 드롭다운 (자세히 알아보기, 도움말, 언어) 개선
  footerButtons.forEach((button) => {
    const container = button.closest(".footer-button-container");
    const dropdown = container.querySelector(".footer-dropdown");

    // 호버 이벤트로 변경
    container.addEventListener("mouseenter", function () {
      // 다른 모든 드롭다운 닫기
      document.querySelectorAll(".footer-dropdown").forEach((el) => {
        if (el !== dropdown) {
          el.classList.remove("show");
        }
      });

      // 현재 드롭다운 표시
      if (dropdown) {
        dropdown.classList.add("show");
      }
    });

    // 마우스 떠날 때 타이머로 지연 닫기
    container.addEventListener("mouseleave", function () {
      setTimeout(() => {
        // 마우스가 드롭다운 위에 없을 때만 닫기
        if (!dropdown.matches(":hover")) {
          dropdown.classList.remove("show");
        }
      }, 400); // 400ms 지연
    });

    // 드롭다운에 마우스 떠날 때 닫기
    if (dropdown) {
      dropdown.addEventListener("mouseleave", function () {
        setTimeout(() => {
          // 마우스가 버튼 위에 없을 때만 닫기
          if (!container.matches(":hover")) {
            dropdown.classList.remove("show");
          }
        }, 200); // 200ms 지연
      });
    }
  });

  // 로그 다이어리 버튼 클릭 이벤트
  if (logDiaryBtn) {
    logDiaryBtn.addEventListener("click", function () {
      toggleLogDiary();
    });
  }

  // 로그 다이어리 닫기 버튼
  if (closeLogDiaryBtn) {
    closeLogDiaryBtn.addEventListener("click", function () {
      toggleLogDiary(false);
    });
  }

  // 로그 다이어리 토글
  function toggleLogDiary(show) {
    if (show === undefined) {
      logDiaryPanel.classList.toggle("open");
    } else if (show) {
      logDiaryPanel.classList.add("open");
    } else {
      logDiaryPanel.classList.remove("open");
    }

    // 대화 기록 표시
    if (logDiaryPanel.classList.contains("open")) {
      updateLogDiary();
    }
  }

  // 퀵 액션 버튼에 툴팁 추가
  if (quickActionBtns) {
    quickActionBtns.forEach((btn) => {
      const icon = btn.querySelector("i");

      // 툴팁 추가
      const tooltip = document.createElement("span");
      tooltip.classList.add("quick-tooltip");
      tooltip.style.display = "none";

      if (icon.classList.contains("fa-cog")) {
        tooltip.textContent = "설정";
      } else if (icon.classList.contains("fa-user-plus")) {
        tooltip.textContent = "멤버 초대";
      }

      btn.appendChild(tooltip);

      // 마우스 오버 시 툴팁 표시
      btn.addEventListener("mouseenter", function () {
        tooltip.style.display = "block";
      });

      // 마우스 아웃 시 툴팁 숨김
      btn.addEventListener("mouseleave", function () {
        tooltip.style.display = "none";
      });

      // 빠른 액션 버튼 이벤트
      btn.addEventListener("click", function (e) {
        e.stopPropagation(); // 이벤트 버블링 방지

        if (icon.classList.contains("fa-cog")) {
          alert("설정 화면으로 이동합니다.");
        } else if (icon.classList.contains("fa-user-plus")) {
          alert("멤버 초대 화면으로 이동합니다.");
        }
      });
    });
  }

  // 즐겨찾기 버튼 클릭 이벤트
  if (favoriteBtn) {
    favoriteBtn.addEventListener("click", function () {
      if (currentTaskId) {
        toggleFavorite(currentTaskId);
      }
    });
  }

  // 공유 버튼 클릭 이벤트
  if (shareBtn) {
    shareBtn.addEventListener("click", function () {
      if (currentTaskId && taskData[currentTaskId]) {
        const taskTitle = taskData[currentTaskId].title;
        // 가상의 공유 URL 생성
        const shareUrl = `${window.location.origin}/share/${currentTaskId}`;

        // 실제 구현에서는 공유 모달, 클립보드 복사 등 구현
        alert(
          `"${taskTitle}" 작업 공유 링크가 클립보드에 복사되었습니다:\n${shareUrl}`
        );

        // 클립보드 복사 시도
        try {
          navigator.clipboard.writeText(shareUrl);
        } catch (err) {
          console.error("클립보드 복사 실패:", err);
        }
      }
    });
  }

  // 이름 변경 이벤트
  if (renameButton) {
    renameButton.addEventListener("click", function (e) {
      e.stopPropagation();
      const currentTitle = taskTitle.textContent;
      const newTitle = prompt("작업 제목을 입력하세요:", currentTitle);

      if (newTitle !== null && newTitle.trim() !== "") {
        taskTitle.textContent = newTitle;

        // Django API를 통한 제목 업데이트
        if (currentTaskId) {
          fetch(apiUrls.updateTaskTitle, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
              task_id: currentTaskId,
              title: newTitle,
            }),
          })
            .then((response) => response.json())
            .then((data) => {
              // 작업 데이터 업데이트
              if (taskData[currentTaskId]) {
                taskData[currentTaskId].title = newTitle;

                // 히스토리 항목도 업데이트
                updateTaskTitle(currentTaskId, newTitle);

                // 로컬 스토리지에 저장
                saveLocalData();
              }
            })
            .catch((error) => {
              console.error("Error updating title:", error);
            });
        }
      }

      // 드롭다운 닫기
      if (titleDropdown) {
        titleDropdown.classList.remove("show");
        activeDropdown = null;
      }
    });
  }

  // 삭제 이벤트
  if (deleteButton) {
    deleteButton.addEventListener("click", function (e) {
      e.stopPropagation();
      if (currentTaskId && confirm("현재 작업을 삭제하시겠습니까?")) {
        // Django API를 통한 작업 삭제
        fetch(apiUrls.deleteTask(currentTaskId), {
          method: "DELETE",
          headers: {
            "X-CSRFToken": getCsrfToken(),
          },
        })
          .then((response) => response.json())
          .then((data) => {
            // 작업 데이터에서 제거
            delete taskData[currentTaskId];

            // 히스토리에서 제거
            removeFromHistory(currentTaskId);

            // 즐겨찾기에서도 제거
            const favIndex = favoriteTaskIds.indexOf(currentTaskId);
            if (favIndex !== -1) {
              favoriteTaskIds.splice(favIndex, 1);
            }

            // 로컬 스토리지에 저장
            saveLocalData();

            // 새 작업 페이지로 돌아가기
            welcomePage.style.display = "flex";
            chatPage.style.display = "none";
            currentTaskId = null;

            // 헤더 버튼 가시성 업데이트
            updateHeaderButtonsVisibility();
          })
          .catch((error) => {
            console.error("Error deleting task:", error);
            alert("작업 삭제 중 오류가 발생했습니다.");
          });
      }

      // 드롭다운 닫기
      if (titleDropdown) {
        titleDropdown.classList.remove("show");
        activeDropdown = null;
      }
    });
  }

  // 첫 페이지에서 메인 입력창 처리
  mainEnterBtn.addEventListener("click", function () {
    if (mainInput.value.trim()) {
      processMainInput();
    } else {
      toggleSpeechRecognition("main");
    }
  });

  // 예시 카드 클릭 이벤트
  exampleCards.forEach((card) => {
    card.addEventListener("click", function () {
      const prompt = this.getAttribute("data-prompt");
      if (prompt) {
        mainInput.value = prompt;
        mainInput.dispatchEvent(new Event("input"));
        processMainInput();
      }
    });
  });

  if (newChatBtn) {
    newChatBtn.addEventListener("click", function () {
      // 로그인 여부 확인 로직 제거 (모든 사용자가 사용 가능)

      const activeItems = document.querySelectorAll(".history-item.active");
      activeItems.forEach((item) => {
        item.classList.remove("active");
      });

      welcomePage.style.display = "flex";
      chatPage.style.display = "none";

      // 헤더 중앙의 작업 제목 숨기기
      taskTitle.style.display = "none";

      currentTaskId = null;
      currentConversation = [];

      mainInput.value = "";
      mainInput.dispatchEvent(new Event("input"));
      mainInput.focus();

      // 헤더 버튼 가시성 업데이트
      updateHeaderButtonsVisibility();
    });
  }

  // 메인 입력값 처리 함수 - 로그인 체크 부분 제거
  function processMainInput() {
    const command = mainInput.value.trim();
    if (command === "") return;

    // 로그인 체크 제거됨 - 모든 사용자가 이용 가능

    // 새 작업 ID 생성
    currentTaskId = Date.now().toString();
    currentConversation = [];

    // 웰컴 페이지 숨기고 채팅 페이지 표시
    welcomePage.style.display = "none";
    chatPage.style.display = "flex";

    // 헤더 중앙에 작업 제목 표시 (타이틀바 수정)
    taskTitle.style.display = "block";

    // 헤더 버튼 가시성 업데이트
    updateHeaderButtonsVisibility();

    // 채팅창 초기화
    chatWindow.innerHTML = "";

    // 사용자 메시지 추가
    addMessageToChat("user", command);

    // Django API에 명령어 전송
    fetch(apiUrls.processInput, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        user_input: command,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        // 작업 제목 업데이트
        taskTitle.textContent = data.title;

        // 작업 데이터 저장
        taskData[currentTaskId] = {
          title: data.title,
          conversation: currentConversation,
          steps: data.process,
          completed: false,
          createdAt: new Date().toISOString(),
        };

        // 로컬 스토리지에 저장
        saveLocalData();
        saveConversationState();

        // 사이드바 히스토리에 추가
        addTaskToHistory(currentTaskId, data.title);

        // Reconfirmation Prompt 표시
        addReconfirmationPrompt(data.process);

        // 즐겨찾기 버튼 상태 업데이트
        if (favoriteBtn) {
          favoriteBtn.innerHTML = favoriteTaskIds.includes(currentTaskId)
            ? '<i class="fas fa-star"></i><span class="tooltip">즐겨찾기됨</span>'
            : '<i class="far fa-star"></i><span class="tooltip">즐겨찾기</span>';
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        addMessageToChat(
          "system",
          "명령어 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        );

        // 개발 환경에서 테스트 용도로 더미 데이터 사용 (오류 상황 처리)
        taskTitle.textContent = "테스트 작업";
        const dummySteps = ["테스트 단계 1", "테스트 단계 2", "테스트 단계 3"];

        // 작업 데이터 저장
        taskData[currentTaskId] = {
          title: "테스트 작업",
          conversation: currentConversation,
          steps: dummySteps,
          completed: false,
          createdAt: new Date().toISOString(),
        };

        // 로컬 스토리지에 저장
        saveLocalData();

        // 사이드바 히스토리에 추가
        addTaskToHistory(currentTaskId, "테스트 작업");

        // Reconfirmation Prompt 표시
        addReconfirmationPrompt(dummySteps);
      });

    // 입력창 초기화
    mainInput.value = "";
    mainInput.dispatchEvent(new Event("input"));
  }

  // 히스토리 아이템 클릭 이벤트 위임
  taskList.addEventListener("click", function (event) {
    const historyItem = event.target.closest(".history-item");
    if (historyItem) {
      const taskId = historyItem.getAttribute("data-id");
      loadTask(taskId);
    }
  });

  // 즐겨찾기 아이템 클릭 이벤트 위임
  if (favoritesList) {
    favoritesList.addEventListener("click", function (event) {
      const historyItem = event.target.closest(".history-item");
      if (historyItem) {
        const taskId = historyItem.getAttribute("data-id");
        loadTask(taskId);
      }
    });
  }

  // 카테고리 탭 전환
  tabButtons.forEach((button) => {
    button.addEventListener("click", function () {
      document.querySelector(".tab-button.active").classList.remove("active");
      this.classList.add("active");

      const category = this.getAttribute("data-category");
      document.querySelectorAll(".task-container").forEach((container) => {
        container.style.display = "none";
      });

      if (category === "recent") {
        document.getElementById("recentTasksContainer").style.display = "flex";
      } else if (category === "favorites") {
        document.getElementById("favoritesContainer").style.display = "flex";
      }
    });
  });

  // 로그 다이어리 업데이트
  function updateLogDiary() {
    const logContent = logDiaryPanel.querySelector(".log-diary-content");
    logContent.innerHTML = "";

    if (
      currentTaskId &&
      taskData[currentTaskId] &&
      taskData[currentTaskId].conversation
    ) {
      const conversation = taskData[currentTaskId].conversation;

      conversation.forEach((entry, index) => {
        const logEntry = document.createElement("div");
        logEntry.classList.add("log-entry");

        const timestamp = document.createElement("div");
        timestamp.classList.add("log-timestamp");
        timestamp.textContent = entry.timestamp || `#${index + 1}`;

        const message = document.createElement("div");
        message.classList.add("log-message");
        message.textContent = `${entry.type === "user" ? "사용자: " : "BlueAI: "}${entry.content}`;

        logEntry.appendChild(timestamp);
        logEntry.appendChild(message);
        logContent.appendChild(logEntry);
      });
    }
  }

  // 작업 목록 로드
  function loadTasks() {
    // 로그인 상태가 아니면 작업 목록을 로드하지 않음
    if (window.isAuthenticated !== true) {
      return;
    }

    // 서버 API 요청
    fetch(apiUrls.getTasks)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((tasks) => {
        if (tasks.length === 0) {
          return;
        }

        tasks.forEach((task) => {
          taskData[task.id] = {
            title: task.title,
            conversation: task.conversation || [],
            steps: task.process || [],
            completed: task.completed || false,
            createdAt: task.created_at,
          };
        });

        // 로컬 스토리지에 저장
        saveLocalData();

        // 작업 목록 UI 업데이트
        populateTaskList();

        // 대화 상태 복원 시도
        if (
          chatPage.style.display === "none" &&
          !window.location.hash.includes("chat")
        ) {
          restoreConversationState();
        }
      })
      .catch((error) => {
        console.error("Error loading tasks:", error);
        // 오류 발생 시 로컬 데이터 사용
        populateTaskList();
      });
  }

  // 작업 목록 UI 업데이트
  function populateTaskList() {
    // 작업 목록 초기화
    taskList.innerHTML = "";

    // 최신 작업부터 표시하기 위한 정렬
    const sortedTasks = Object.keys(taskData).sort((a, b) => {
      const dateA = new Date(taskData[a].createdAt || 0);
      const dateB = new Date(taskData[b].createdAt || 0);
      return dateB - dateA;
    });

    // 작업 목록에 추가
    sortedTasks.forEach((id) => {
      addTaskToHistory(id, taskData[id].title, false);
    });

    // 전체 보기 버튼 표시 (5개 이상일 때)
    if (sortedTasks.length > 5 && viewAllTasks) {
      viewAllTasks.style.display = "block";
    }
  }

  // 즐겨찾기 로드
  function loadFavorites() {
    // 로그인 상태가 아니면 즐겨찾기를 로드하지 않음
    if (window.isAuthenticated !== true) {
      return;
    }

    // 서버 API에서 즐겨찾기 목록 가져오기
    fetch(apiUrls.getFavorites)
      .then((response) => response.json())
      .then((favorites) => {
        // 서버에서 가져온 즐겨찾기 ID 저장
        favoriteTaskIds = favorites.map((fav) => String(fav.id));

        // 로컬 스토리지에 저장
        saveLocalData();

        // 즐겨찾기 목록 UI 업데이트
        updateFavoritesList();
      })
      .catch((error) => {
        console.error("Error loading favorites:", error);
        // 오류 발생 시 로컬 데이터 사용
        const storedFavorites = localStorage.getItem("blueai_favorites");
        if (storedFavorites) {
          favoriteTaskIds = JSON.parse(storedFavorites);
          updateFavoritesList();
        }
      });
  }

  // 즐겨찾기 목록 업데이트
  function updateFavoritesList() {
    if (!favoritesList) return;

    favoritesList.innerHTML = "";

    favoriteTaskIds.forEach((id) => {
      if (taskData[id]) {
        const li = document.createElement("li");
        li.classList.add("history-item");
        li.setAttribute("data-id", id);

        const favoriteIcon = document.createElement("span");
        favoriteIcon.classList.add("favorite-icon");
        favoriteIcon.innerHTML = "★";

        li.appendChild(favoriteIcon);
        li.appendChild(document.createTextNode(taskData[id].title));

        favoritesList.appendChild(li);
      }
    });
  }

  // 작업 불러오기
  function loadTask(taskId) {
    // 서버 API에서 작업 상세 정보 가져오기
    fetch(apiUrls.getTask(taskId))
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((task) => {
        welcomePage.style.display = "none";
        chatPage.style.display = "flex";

        // 헤더 중앙에 작업 제목 표시
        taskTitle.style.display = "block";
        taskTitle.textContent = task.title;

        // 헤더 버튼 가시성 업데이트
        updateHeaderButtonsVisibility();

        // 작업 선택 상태 업데이트
        const activeItems = document.querySelectorAll(".history-item.active");
        activeItems.forEach((item) => {
          item.classList.remove("active");
        });

        const historyItems = document.querySelectorAll(
          `.history-item[data-id="${taskId}"]`
        );
        historyItems.forEach((item) => {
          item.classList.add("active");
        });

        // 작업 데이터 업데이트
        currentTaskId = String(taskId);
        currentConversation = task.conversation || [];

        // 로컬 스토리지에도 업데이트
        taskData[currentTaskId] = {
          title: task.title,
          conversation: task.conversation || [],
          steps: task.process || [],
          completed: task.completed || false,
          createdAt: task.created_at,
        };
        saveLocalData();
        saveConversationState();

        // 채팅 창 초기화
        chatWindow.innerHTML = "";

        if (currentConversation.length > 0) {
          // 저장된 대화 표시
          currentConversation.forEach((msg) => {
            const messageDiv = document.createElement("div");
            messageDiv.classList.add("message");

            if (msg.type === "user") {
              messageDiv.classList.add("user-message");
            } else if (msg.type === "system") {
              messageDiv.classList.add("system-message");
            } else {
              messageDiv.classList.add("assistant-message");
            }

            messageDiv.innerHTML = `<p>${msg.content}</p>`;
            chatWindow.appendChild(messageDiv);
          });

          // 작업이 완료되지 않았고 재확인 단계가 있다면 다시 표시
          if (!task.completed && task.process && task.process.length > 0) {
            // 저장된 리컨펌 프롬프트 상태가 있으면 복원
            if (taskData[currentTaskId].promptState) {
              restoreReconfirmationPrompt(taskData[currentTaskId].promptState);
            } else {
              addReconfirmationPrompt(task.process);
            }
          }
        } else {
          addMessageToChat(
            "system",
            "안녕하세요! BlueAI입니다. 어떤 작업을 도와드릴까요?"
          );
        }

        // 즐겨찾기 버튼 상태 업데이트
        if (favoriteBtn) {
          const isFavorite =
            task.is_favorite || favoriteTaskIds.includes(currentTaskId);
          favoriteBtn.innerHTML = isFavorite
            ? '<i class="fas fa-star"></i><span class="tooltip">즐겨찾기됨</span>'
            : '<i class="far fa-star"></i><span class="tooltip">즐겨찾기</span>';
        }

        scrollToBottom();
      })
      .catch((error) => {
        console.error("Error loading task:", error);

        // 로컬 데이터로 폴백
        if (taskData[taskId]) {
          welcomePage.style.display = "none";
          chatPage.style.display = "flex";

          taskTitle.style.display = "block";
          taskTitle.textContent = taskData[taskId].title;

          updateHeaderButtonsVisibility();

          const activeItems = document.querySelectorAll(".history-item.active");
          activeItems.forEach((item) => {
            item.classList.remove("active");
          });

          const historyItems = document.querySelectorAll(
            `.history-item[data-id="${taskId}"]`
          );
          historyItems.forEach((item) => {
            item.classList.add("active");
          });

          currentTaskId = taskId;
          currentConversation = taskData[taskId].conversation || [];

          chatWindow.innerHTML = "";

          if (currentConversation.length > 0) {
            // 로컬 대화 표시
            currentConversation.forEach((msg) => {
              const messageDiv = document.createElement("div");
              messageDiv.classList.add("message");

              if (msg.type === "user") {
                messageDiv.classList.add("user-message");
              } else if (msg.type === "system") {
                messageDiv.classList.add("system-message");
              } else {
                messageDiv.classList.add("assistant-message");
              }

              messageDiv.innerHTML = `<p>${msg.content}</p>`;
              chatWindow.appendChild(messageDiv);
            });
          } else {
            addMessageToChat(
              "system",
              "안녕하세요! BlueAI입니다. 어떤 작업을 도와드릴까요?"
            );
          }

          if (favoriteBtn) {
            favoriteBtn.innerHTML = favoriteTaskIds.includes(currentTaskId)
              ? '<i class="fas fa-star"></i><span class="tooltip">즐겨찾기됨</span>'
              : '<i class="far fa-star"></i><span class="tooltip">즐겨찾기</span>';
          }

          scrollToBottom();
        } else {
          alert("작업을 불러오는데 실패했습니다.");
        }
      });
  }

  // 파일 업로드 버튼 동작
  fileUploadBtn.addEventListener("click", function () {
    fileUpload.click();
  });

  fileUpload.addEventListener("change", function (event) {
    const files = event.target.files;
    if (files.length > 0) {
      addMessageToChat(
        "system",
        `파일 "${files[0].name}"이(가) 업로드되었습니다.`
      );
    }
  });

  // 명령어 입력 및 처리
  enterBtn.addEventListener("click", function () {
    // 마이크 아이콘이 표시 중이면 음성 인식 토글
    if (this.querySelector(".mic-icon").style.display !== "none") {
      toggleSpeechRecognition("chat");
    } else {
      // 전송 아이콘이 표시 중이면 명령어 처리
      processCommand();
    }
  });

  // 음성 인식 토글 (브라우저 지원 여부에 따라) - 수정
  function toggleSpeechRecognition(inputType) {
    if (
      !("webkitSpeechRecognition" in window) &&
      !("SpeechRecognition" in window)
    ) {
      alert(
        "죄송합니다. 음성 인식 기능이 현재 브라우저에서 지원되지 않습니다."
      );
      return;
    }

    const targetBtn = inputType === "main" ? mainEnterBtn : enterBtn;

    if (isListening) {
      // 음성 인식 중지
      isListening = false;
      targetBtn.classList.remove("recording");

      // 테스트용: 마이크 버튼 클릭 시 "음성으로 인식된 텍스트 예시입니다." 입력
      const targetInput = inputType === "main" ? mainInput : userInput;
      targetInput.value = "음성으로 인식된 텍스트 예시입니다.";
      targetInput.dispatchEvent(new Event("input"));
    } else {
      // 음성 인식 시작
      isListening = true;
      targetBtn.classList.add("recording");

      // 마이크 활성화 상태를 유지 (자동으로 끄지 않음)
      // 사용자가 다시 클릭할 때까지 상태 유지
    }
  }

  // 명령어 처리 함수
  function processCommand() {
    const command = userInput.value.trim();
    if (command === "") return;

    addMessageToChat("user", command);
    userInput.value = "";
    adjustTextareaHeight(userInput);
    userInput.focus();

    // Django API에 명령어 전송
    fetch(apiUrls.processInput, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        user_input: command,
        task_id: currentTaskId,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        // 작업 데이터에 단계 저장
        if (taskData[currentTaskId]) {
          taskData[currentTaskId].steps = data.process;
          saveLocalData();
          saveConversationState();
        }

        // Reconfirmation Prompt 표시
        addReconfirmationPrompt(data.process);
      })
      .catch((error) => {
        console.error("Error:", error);
        addMessageToChat(
          "system",
          "명령어 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        );

        // 개발 환경 테스트용 - 오류 발생 시에도 UI 표시
        if (taskData[currentTaskId]) {
          const dummySteps = [
            "테스트 단계 1",
            "테스트 단계 2",
            "테스트 단계 3",
          ];
          taskData[currentTaskId].steps = dummySteps;
          saveLocalData();
          addReconfirmationPrompt(dummySteps);
        }
      });
  }

  // 메시지 추가 함수
  function addMessageToChat(type, content) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message");

    if (type === "user") {
      messageDiv.classList.add("user-message");
    } else if (type === "system") {
      messageDiv.classList.add("system-message");
    } else {
      messageDiv.classList.add("assistant-message");
    }

    messageDiv.innerHTML = `<p>${content}</p>`;
    chatWindow.appendChild(messageDiv);
    scrollToBottom();

    if (currentTaskId) {
      const timestamp = new Date().toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
      });

      if (!currentConversation) {
        currentConversation = [];
      }

      currentConversation.push({
        type: type,
        content: content,
        timestamp: timestamp,
      });

      if (taskData[currentTaskId]) {
        taskData[currentTaskId].conversation = currentConversation;
        saveLocalData();
        saveConversationState();
      }

      // Django API에 대화 기록 업데이트 요청
      fetch(apiUrls.updateConversation, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          task_id: currentTaskId,
          conversation: currentConversation,
        }),
      }).catch((error) => {
        console.error("Error updating conversation:", error);
      });
    }
  }

  // 히스토리에 작업 추가
  function addTaskToHistory(id, title, setActive = true) {
    const existingItem = document.querySelector(
      `.history-item[data-id="${id}"]`
    );
    if (existingItem) {
      if (setActive) {
        // 기존 활성화 항목 비활성화
        const activeItems = document.querySelectorAll(".history-item.active");
        activeItems.forEach((item) => {
          item.classList.remove("active");
        });

        // 이 항목 활성화
        existingItem.classList.add("active");
      }
      return;
    }

    if (setActive) {
      // 기존 활성화 항목 비활성화
      const activeItems = document.querySelectorAll(".history-item.active");
      activeItems.forEach((item) => {
        item.classList.remove("active");
      });
    }

    // 새로운 항목 생성
    const li = document.createElement("li");
    li.classList.add("history-item");
    if (setActive) {
      li.classList.add("active");
    }
    li.setAttribute("data-id", id);

    if (favoriteTaskIds.includes(id)) {
      const favoriteIcon = document.createElement("span");
      favoriteIcon.classList.add("favorite-icon");
      favoriteIcon.innerHTML = "★";
      li.appendChild(favoriteIcon);
    }

    li.appendChild(document.createTextNode(title));

    if (taskList.firstChild) {
      taskList.insertBefore(li, taskList.firstChild);
    } else {
      taskList.appendChild(li);
    }
  }

  // 히스토리에서 작업 제거
  function removeFromHistory(id) {
    const historyItems = document.querySelectorAll(
      `.history-item[data-id="${id}"]`
    );
    historyItems.forEach((item) => {
      item.remove();
    });
  }

  // 작업 제목 업데이트
  function updateTaskTitle(id, newTitle) {
    const historyItems = document.querySelectorAll(
      `.history-item[data-id="${id}"]`
    );
    historyItems.forEach((item) => {
      const favoriteIcon = item.querySelector(".favorite-icon");

      item.innerHTML = "";

      if (favoriteIcon) {
        item.appendChild(favoriteIcon.cloneNode(true));
      }

      item.appendChild(document.createTextNode(newTitle));
    });
  }

  // 즐겨찾기 토글
  function toggleFavorite(id) {
    // Django API를 통한 즐겨찾기 토글
    fetch(apiUrls.toggleFavorite(id), {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.is_favorite) {
          // 즐겨찾기에 추가됨
          if (!favoriteTaskIds.includes(id)) {
            favoriteTaskIds.push(id);
          }
          // 즐겨찾기 버튼 상태 업데이트
          if (favoriteBtn) {
            favoriteBtn.innerHTML =
              '<i class="fas fa-star"></i><span class="tooltip">즐겨찾기됨</span>';
          }

          // 히스토리 항목에 아이콘 추가
          const historyItems = document.querySelectorAll(
            `.history-item[data-id="${id}"]`
          );
          historyItems.forEach((item) => {
            if (!item.querySelector(".favorite-icon")) {
              const favoriteIcon = document.createElement("span");
              favoriteIcon.classList.add("favorite-icon");
              favoriteIcon.innerHTML = "★";
              item.insertBefore(favoriteIcon, item.firstChild);
            }
          });
        } else {
          // 즐겨찾기에서 제거됨
          const index = favoriteTaskIds.indexOf(id);
          if (index !== -1) {
            favoriteTaskIds.splice(index, 1);
          }

          // 즐겨찾기 버튼 상태 업데이트
          if (favoriteBtn) {
            favoriteBtn.innerHTML =
              '<i class="far fa-star"></i><span class="tooltip">즐겨찾기</span>';
          }

          // 히스토리 항목에서 아이콘 제거
          const historyItems = document.querySelectorAll(
            `.history-item[data-id="${id}"]`
          );
          historyItems.forEach((item) => {
            const favoriteIcon = item.querySelector(".favorite-icon");
            if (favoriteIcon) {
              favoriteIcon.remove();
            }
          });
        }

        // 로컬 스토리지에 저장
        saveLocalData();

        // 즐겨찾기 목록 업데이트
        updateFavoritesList();
      })
      .catch((error) => {
        console.error("Error toggling favorite:", error);

        // 오류 시 로컬 처리로 폴백
        const index = favoriteTaskIds.indexOf(id);

        if (index === -1) {
          // 즐겨찾기에 추가
          favoriteTaskIds.push(id);

          // 히스토리 항목에 아이콘 추가
          const historyItems = document.querySelectorAll(
            `.history-item[data-id="${id}"]`
          );
          historyItems.forEach((item) => {
            if (!item.querySelector(".favorite-icon")) {
              const favoriteIcon = document.createElement("span");
              favoriteIcon.classList.add("favorite-icon");
              favoriteIcon.innerHTML = "★";
              item.insertBefore(favoriteIcon, item.firstChild);
            }
          });

          // 즐겨찾기 버튼 업데이트
          if (favoriteBtn) {
            favoriteBtn.innerHTML =
              '<i class="fas fa-star"></i><span class="tooltip">즐겨찾기됨</span>';
          }
        } else {
          // 즐겨찾기에서 제거
          favoriteTaskIds.splice(index, 1);

          // 히스토리 항목에서 아이콘 제거
          const historyItems = document.querySelectorAll(
            `.history-item[data-id="${id}"]`
          );
          historyItems.forEach((item) => {
            const favoriteIcon = item.querySelector(".favorite-icon");
            if (favoriteIcon) {
              favoriteIcon.remove();
            }
          });

          // 즐겨찾기 버튼 업데이트
          if (favoriteBtn) {
            favoriteBtn.innerHTML =
              '<i class="far fa-star"></i><span class="tooltip">즐겨찾기</span>';
          }
        }

        // 로컬 스토리지에 저장
        saveLocalData();

        // 즐겨찾기 목록 업데이트
        updateFavoritesList();
      });
  }

  // Reconfirmation Prompt 추가
  function addReconfirmationPrompt(steps) {
    if (!steps || !Array.isArray(steps) || steps.length === 0) {
      addMessageToChat(
        "system",
        "명령어 처리 중 오류가 발생했습니다. 단계 정보가 올바르지 않습니다."
      );
      return;
    }

    let html = `
        <div class="reconfirmation-prompt" id="reconfirmPrompt_${currentTaskId}">
            <h3>작업 확인</h3>
            <p>다음 작업을 수행하시겠습니까?</p>
            <div class="task-steps">
        `;

    steps.forEach((step, index) => {
      html += `
            <div class="task-step">
                <div class="step-header">
                    <span class="step-number">${index + 1}</span>
                    <span class="step-title">${step}</span>
                    <div class="step-actions">
                        <button class="action-button edit" data-index="${index}">✏️</button>
                        <button class="action-button delete" data-index="${index}">❌</button>
                    </div>
                </div>
            </div>
            `;
    });

    html += `
            </div>
            <div class="confirm-buttons">
                <button class="secondary-button cancel-button">취소</button>
                <button class="primary-button continue-button">계속하기</button>
            </div>
        </div>
        `;

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "assistant-message", "persisted");
    messageDiv.setAttribute(
      "data-prompt-id",
      `reconfirmPrompt_${currentTaskId}`
    );
    messageDiv.innerHTML = html;
    chatWindow.appendChild(messageDiv);
    scrollToBottom();

    // 추가된 버튼들에 이벤트 리스너 연결
    attachPromptEventListeners(messageDiv, steps);

    // 대화 기록에 추가
    addMessageToChat(
      "assistant",
      '작업을 실행할 준비가 되었습니다. 위의 단계를 확인하시고, 계속하시려면 "계속하기" 버튼을 클릭하세요.'
    );

    // 작업 데이터에 리컨펌 프롬프트 상태 저장
    if (currentTaskId && taskData[currentTaskId]) {
      taskData[currentTaskId].promptState = {
        steps: steps,
        html: messageDiv.outerHTML, // 전체 HTML을 저장
        completed: false,
      };
      saveLocalData();
      saveConversationState();
    }
  }

  // 저장된 리컨펌 프롬프트 복원
  function restoreReconfirmationPrompt(promptState) {
    if (!promptState || !promptState.steps || promptState.steps.length === 0)
      return;

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "assistant-message", "persisted");
    messageDiv.setAttribute(
      "data-prompt-id",
      `reconfirmPrompt_${currentTaskId}`
    );
    messageDiv.innerHTML = promptState.html || "";

    // 완료 상태면 비활성화 스타일 적용
    if (promptState.completed) {
      const reconfirmPrompt = messageDiv.querySelector(
        ".reconfirmation-prompt"
      );
      if (reconfirmPrompt) {
        reconfirmPrompt.classList.add("completed");
      }
      messageDiv.style.pointerEvents = "none";
      messageDiv.style.opacity = "0.8";
    } else {
      // 이벤트 리스너 연결
      attachPromptEventListeners(messageDiv, promptState.steps);
    }

    chatWindow.appendChild(messageDiv);
    scrollToBottom();
  }

  // 프롬프트 이벤트 리스너 추가
  function attachPromptEventListeners(container, steps) {
    // 편집 버튼 이벤트
    const editButtons = container.querySelectorAll(".edit");
    editButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const index = this.getAttribute("data-index");
        const stepTitle =
          this.closest(".step-header").querySelector(".step-title");
        const currentStep = stepTitle.textContent;
        const newStep = prompt("단계를 수정하세요:", currentStep);

        if (newStep !== null && newStep.trim() !== "") {
          stepTitle.textContent = newStep;
          steps[index] = newStep;

          // 작업 데이터 업데이트
          if (currentTaskId && taskData[currentTaskId]) {
            taskData[currentTaskId].steps = steps;

            // 프롬프트 상태도 업데이트
            if (taskData[currentTaskId].promptState) {
              taskData[currentTaskId].promptState.steps = steps;
              const reconfirmPrompt = container.querySelector(
                ".reconfirmation-prompt"
              );
              if (reconfirmPrompt) {
                taskData[currentTaskId].promptState.html =
                  reconfirmPrompt.outerHTML;
              }
            }

            saveLocalData();
            saveConversationState();
          }
        }
      });
    });

    // 삭제 버튼 이벤트
    const deleteButtons = container.querySelectorAll(".delete");
    deleteButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const index = parseInt(this.getAttribute("data-index"));
        const taskStep = this.closest(".task-step");

        // 배열에서 해당 단계 제거
        steps.splice(index, 1);

        // DOM에서 요소 제거
        taskStep.remove();

        // 번호 재정렬
        const stepNumbers = container.querySelectorAll(".step-number");
        stepNumbers.forEach((step, idx) => {
          step.textContent = idx + 1;
          step
            .closest(".task-step")
            .querySelector(".edit")
            .setAttribute("data-index", idx);
          step
            .closest(".task-step")
            .querySelector(".delete")
            .setAttribute("data-index", idx);
        });

        // 작업 데이터 업데이트
        if (currentTaskId && taskData[currentTaskId]) {
          taskData[currentTaskId].steps = steps;

          // 프롬프트 상태도 업데이트
          if (taskData[currentTaskId].promptState) {
            taskData[currentTaskId].promptState.steps = steps;
            const reconfirmPrompt = container.querySelector(
              ".reconfirmation-prompt"
            );
            if (reconfirmPrompt) {
              taskData[currentTaskId].promptState.html =
                reconfirmPrompt.outerHTML;
            }
          }

          saveLocalData();
          saveConversationState();
        }
      });
    });

    // 계속하기 버튼 이벤트
    const continueButton = container.querySelector(".continue-button");
    if (continueButton) {
      continueButton.addEventListener("click", function () {
        // 실행 중인 모든 단계를 수집
        const currentSteps = Array.from(
          container.querySelectorAll(".step-title")
        ).map((step) => step.textContent);

        // Django API에 실행 요청
        if (currentTaskId) {
          fetch(apiUrls.executeTask, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
              task_id: currentTaskId,
              steps: currentSteps,
            }),
          }).catch((error) => {
            console.error("Error executing task:", error);
          });
        }

        // 작업 실행 시작 메시지
        addMessageToChat("system", "작업을 실행합니다...");

        // 작업 완료 상태로 업데이트
        if (currentTaskId && taskData[currentTaskId]) {
          taskData[currentTaskId].completed = true;

          // 리컨펌 프롬프트에 완료 클래스 추가
          const reconfirmPrompt = container.querySelector(
            ".reconfirmation-prompt"
          );
          if (reconfirmPrompt) {
            reconfirmPrompt.classList.add("completed");

            // 전체 HTML 상태 저장 개선 (innerHTML 대신 outerHTML 사용)
            if (taskData[currentTaskId].promptState) {
              taskData[currentTaskId].promptState.completed = true;
              taskData[currentTaskId].promptState.html = container.innerHTML;
            } else {
              taskData[currentTaskId].promptState = {
                steps: currentSteps,
                completed: true,
                html: container.innerHTML,
              };
            }
          }

          saveLocalData();
          saveConversationState();
        }

        // 각 단계별 실행
        executeSteps(currentSteps);

        // 비활성화 (완전히 제거하지 않고 비활성화만)
        container.style.pointerEvents = "none";
        container.style.opacity = "0.8";
      });
    }

    // 취소 버튼 이벤트
    const cancelButton = container.querySelector(".cancel-button");
    if (cancelButton) {
      cancelButton.addEventListener("click", function () {
        addMessageToChat("system", "작업이 취소되었습니다.");

        // 비활성화 (완전히 제거하지 않고 비활성화만)
        container.style.pointerEvents = "none";
        container.style.opacity = "0.8";

        // 리컨펌 프롬프트에 완료 클래스 추가
        const reconfirmPrompt = container.querySelector(
          ".reconfirmation-prompt"
        );
        if (reconfirmPrompt) {
          reconfirmPrompt.classList.add("completed");

          // 취소 시에도 HTML 상태 저장
          if (currentTaskId && taskData[currentTaskId]) {
            if (taskData[currentTaskId].promptState) {
              taskData[currentTaskId].promptState.completed = true;
              taskData[currentTaskId].promptState.html = container.innerHTML;
            } else {
              taskData[currentTaskId].promptState = {
                steps: steps,
                completed: true,
                html: container.innerHTML,
              };
            }
            saveLocalData();
            saveConversationState();
          }
        }
      });
    }
  }

  // 단계별 실행 함수
  function executeSteps(steps) {
    let currentStep = 0;

    function executeNextStep() {
      if (currentStep < steps.length) {
        const step = steps[currentStep];

        // 실행 중인 단계 메시지 추가
        const inProgressMsg = `${currentStep + 1}. ${step} - 진행 중...`;
        const messageDiv = document.createElement("div");
        messageDiv.classList.add(
          "message",
          "system-message",
          "progress-message",
          "in-progress"
        );
        messageDiv.innerHTML = `
                    <p>${inProgressMsg}</p>
                    <div class="progress-indicator">
                        <div class="progress-bar"></div>
                    </div>
                `;
        chatWindow.appendChild(messageDiv);
        scrollToBottom();

        // 실제로는 이 부분에서 서버 API를 호출하여 작업 실행

        // 예시 목적으로 타이머 사용
        setTimeout(() => {
          // 진행 중 메시지 제거
          chatWindow.removeChild(messageDiv);

          // 완료 메시지
          const completedMsg = `${currentStep + 1}. ${step} - 완료!`;
          addMessageToChat("system", completedMsg);

          // 다음 단계 실행
          currentStep++;
          executeNextStep();
        }, 1500);
      } else {
        // 모든 단계 완료
        setTimeout(() => {
          addMessageToChat(
            "assistant",
            "모든 작업이 완료되었습니다. 결과를 확인해주세요."
          );
        }, 500);
      }
    }

    // 첫 번째 단계부터 실행 시작
    executeNextStep();
  }

  // 채팅창 스크롤 함수
  function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  // 메인 페이지에서는 특정 버튼 숨기기
  function updateHeaderButtonsVisibility() {
    // 메인 페이지일 때
    if (welcomePage.style.display !== "none") {
      // 공유, 즐겨찾기, 로그 다이어리 버튼 숨기기
      if (shareBtn) shareBtn.style.display = "none";
      if (favoriteBtn) favoriteBtn.style.display = "none";
      if (logDiaryBtn) logDiaryBtn.style.display = "none";
    } else {
      // 채팅 페이지일 때는 표시
      if (shareBtn) shareBtn.style.display = "inline-block";
      if (favoriteBtn) favoriteBtn.style.display = "inline-block";
      if (logDiaryBtn) logDiaryBtn.style.display = "inline-block";
    }
  }

  // 전체 작업 보기 모달
  if (viewAllTasks) {
    viewAllTasks.addEventListener("click", function () {
      const modalContent = allTasksModal.querySelector(".all-tasks-list");
      modalContent.innerHTML = "";

      // 모든 작업 목록 표시 (최신순 정렬)
      const sortedTasks = Object.keys(taskData).sort((a, b) => {
        const dateA = new Date(taskData[a].createdAt || 0);
        const dateB = new Date(taskData[b].createdAt || 0);
        return dateB - dateA;
      });

      sortedTasks.forEach((id) => {
        const task = taskData[id];
        const taskItem = document.createElement("div");
        taskItem.classList.add("task-item");
        taskItem.setAttribute("data-id", id);

        const title = document.createElement("div");
        title.classList.add("task-item-title");
        title.textContent = task.title;

        const date = document.createElement("div");
        date.classList.add("task-item-date");

        // 날짜 형식 설정
        let dateText = "생성: ";
        if (task.createdAt) {
          const taskDate = new Date(task.createdAt);
          dateText += taskDate.toLocaleDateString("ko-KR", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
          });
        } else {
          dateText += "알 수 없음";
        }

        date.textContent = dateText;

        taskItem.appendChild(title);
        taskItem.appendChild(date);
        modalContent.appendChild(taskItem);

        // 클릭 이벤트
        taskItem.addEventListener("click", function () {
          const taskId = this.getAttribute("data-id");
          loadTask(taskId);
          allTasksModal.style.display = "none";
        });
      });

      // 모달 표시
      allTasksModal.style.display = "flex";
    });

    // 모달 닫기 버튼
    const modalClose = allTasksModal.querySelector(".modal-close");
    if (modalClose) {
      modalClose.addEventListener("click", function () {
        allTasksModal.style.display = "none";
      });
    }

    // 모달 외부 클릭 시 닫기
    allTasksModal.addEventListener("click", function (e) {
      if (e.target === allTasksModal) {
        allTasksModal.style.display = "none";
      }
    });
  }

  // 초기화 시 헤더 버튼 가시성 업데이트
  updateHeaderButtonsVisibility();

  // 페이지 로드 시 입력창에 마이크 아이콘 표시 및 버튼 색상 설정
  document
    .querySelectorAll(".send-button, .main-enter-btn")
    .forEach((button) => {
      const sendIcon = button.querySelector(".send-icon");
      const micIcon = button.querySelector(".mic-icon");
      if (sendIcon && micIcon) {
        sendIcon.style.display = "none";
        micIcon.style.display = "inline-block";
      }
    });

  // 초기화 시 입력창 사이즈 조정
  adjustTextareaHeight(mainInput);
  adjustTextareaHeight(userInput);

  // 로그아웃 폼 처리
  const logoutForm = document.getElementById("logout-form");
  if (logoutForm) {
    logoutForm.addEventListener("submit", function () {
      // 로그아웃 전 필요한 정리 작업
      localStorage.removeItem("blueai_current_conversation");
    });
  }

  // 페이지 로드 시 대화 복원 시도
  if (
    welcomePage.style.display !== "none" &&
    !window.location.hash.includes("chat")
  ) {
    setTimeout(() => {
      restoreConversationState();
    }, 500);
  }

  // 프로젝트 아이템 클릭 이벤트 처리
  const projectItems = document.querySelectorAll(".project-item");
  if (projectItems.length > 0) {
    projectItems.forEach((item) => {
      item.addEventListener("click", function () {
        const projectId = this.getAttribute("data-project-id");

        // 프로젝트 전환 API 호출
        fetch(apiUrls.switchProject, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            project_id: projectId,
          }),
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.status === "success") {
              // 성공 메시지 표시
              alert(data.message);

              // 페이지 새로고침 (프로젝트 변경사항 적용)
              window.location.reload();
            } else {
              alert(data.message || "프로젝트 전환 중 오류가 발생했습니다.");
            }
          })
          .catch((error) => {
            console.error("Error switching project:", error);
            alert("프로젝트 전환 중 오류가 발생했습니다.");
          });

        // 드롭다운 닫기
        const dropdown = document.querySelector(".user-dropdown");
        if (dropdown) {
          dropdown.classList.remove("show");
        }
      });
    });
  }

  // 로그아웃 버튼 제출 처리 개선
  const logoutButton = document.querySelector(".logout-button");

  if (logoutForm && logoutButton) {
    logoutButton.addEventListener("click", function (e) {
      e.preventDefault();

      // 로그아웃 전 필요한 정리 작업
      localStorage.removeItem("blueai_current_conversation");

      // 폼 제출
      logoutForm.submit();
    });
  }

  // 로그인 상태와 관계없이 새 채팅 버튼 표시
  function updateNewChatButtonVisibility() {
    if (newChatBtn) {
      newChatBtn.style.display = "flex"; // flex로 변경하여 중앙 정렬 용이하게
    }
  }

  // 초기화 시 실행
  updateNewChatButtonVisibility();
});
