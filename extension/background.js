chrome.action.onClicked.addListener((tab) => {
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: (tabUrl) => {
      if (document.getElementById("qa-box")) return;

      
      const box = document.createElement("div");
      box.id = "qa-box";
      Object.assign(box.style, {
        position: "fixed", top: "20px", right: "20px",
        width: "320px", minWidth: "280px", minHeight: "200px",
        background: "#1e1e1e", color: "white", padding: "15px",
        borderRadius: "10px", zIndex: "999999", fontSize: "14px",
        boxShadow: "0 4px 15px rgba(0,0,0,0.5)",
        cursor: "grab",
        resize: "both", overflow: "hidden",
        display: "flex", flexDirection: "column",
        fontFamily: "Arial, sans-serif"
      });

      
      box.innerHTML = `
        <style>
          .btn-primary:active { transform: scale(0.96); background: #0056b3 !important; }
          .btn-primary:hover { background: #0069d9 !important; }
          .btn-nav:hover { background: #444 !important; }
          input:focus, textarea:focus, select:focus { outline: 1px solid #007bff; border-color: transparent; }
          .view-container { display: none; flex-direction: column; flex-grow: 1; }
          .active-view { display: flex; }
          .input-field { width: 100%; margin-bottom: 10px; background: #222; color: white; border: 1px solid #555; border-radius: 4px; padding: 8px; box-sizing: border-box; }
        </style>

        <div style="font-weight:bold; margin-bottom:10px; border-bottom:1px solid #444; padding-bottom:5px; flex-shrink:0; display:flex; justify-content:space-between; align-items:center;">
          <span id="box-title">QA Control Panel</span>
          <button id="close" style="color:red; cursor:pointer; background:none; border:none; font-weight:bold; font-size:16px;">✕</button>
        </div>
        
        <!-- View 1: Main Page -->
        <div id="main-view" class="view-container active-view">
          <button id="go-ui-test" class="btn-nav" style="width:100%; background:#333; color:white; border:1px solid #555; padding:12px; margin-bottom:10px; cursor:pointer; border-radius:4px; font-weight:bold; transition:all 0.2s;">🖥️ UI Test</button>
          <button id="go-perf-test" class="btn-nav" style="width:100%; background:#333; color:white; border:1px solid #555; padding:12px; cursor:pointer; border-radius:4px; font-weight:bold; transition:all 0.2s;">🚀 Performance Test</button>
        </div>

        <!-- View 2: UI Test Page -->
        <div id="ui-test-view" class="view-container">
          <button class="back-btn btn-nav" style="background:none; border:none; color:#007bff; text-align:left; cursor:pointer; margin-bottom:10px; padding:0;">← Back</button>
          
          <label style="font-size:12px; margin-bottom:4px;">Test Type:</label>
          <select id="ui-mode" class="input-field" style="background:#333;">
            <option value="manual_test">Manual Test</option>
            <option value="scripted_test">Scripted Test</option>
            <option value="scenario_test">Scenario Test</option>
          </select>
          
          <textarea id="ui-scenario-text" class="input-field" placeholder="Enter scenario..." style="height:80px; display:none; resize:none;"></textarea>
          
          <div style="flex-grow:1;"></div>
          <button class="run-btn btn-primary" data-category="ui_test" style="width:100%; background:#007bff; color:white; border:none; padding:10px; cursor:pointer; border-radius:4px; font-weight:bold; transition: all 0.2s ease;">Run UI Action</button>
        </div>

        <!-- View 3: Performance Test Page -->
        <div id="perf-test-view" class="view-container">
          <button class="back-btn btn-nav" style="background:none; border:none; color:#007bff; text-align:left; cursor:pointer; margin-bottom:10px; padding:0;">← Back</button>
          
          <label style="font-size:12px; margin-bottom:4px;">Locust Test Type:</label>
          <select id="perf-mode" class="input-field" style="background:#333;">
            <option value="load_test">Load Test</option>
            <option value="stress_test">Stress Test</option>
            <option value="spike_test">Spike Test</option>
            <option value="endurance_test">Endurance Test</option>
          </select>

          <div style="display:flex; gap:10px;">
            <div style="flex:1;">
              <label style="font-size:12px; margin-bottom:4px; display:block;">Users:</label>
              <input type="number" id="perf-users" class="input-field" placeholder="e.g. 100" value="10">
            </div>
            <div style="flex:1;">
              <label style="font-size:12px; margin-bottom:4px; display:block;">Duration:</label>
              <input type="text" id="perf-duration" class="input-field" placeholder="e.g. 30s" value="30s">
            </div>
          </div>
          
          <div style="flex-grow:1;"></div>
          <button class="run-btn btn-primary" data-category="performance_test" style="width:100%; background:#28a745; color:white; border:none; padding:10px; cursor:pointer; border-radius:4px; font-weight:bold; transition: all 0.2s ease;">Run Performance Action</button>
        </div>

        <!-- Status Area (Shared across all views) -->
        <div id="status" style="margin-top:15px; font-size:12px; color:#aaa; flex-shrink:0; text-align:center; border-top:1px solid #444; padding-top:10px;">Ready</div>
      `;
      document.body.appendChild(box);

     
      const mainView = box.querySelector("#main-view");
      const uiTestView = box.querySelector("#ui-test-view");
      const perfTestView = box.querySelector("#perf-test-view");
      const statusDiv = box.querySelector("#status");
      const titleSpan = box.querySelector("#box-title");

      
      const uiModeSelect = box.querySelector("#ui-mode");
      const uiTextArea = box.querySelector("#ui-scenario-text");

      
      const perfModeSelect = box.querySelector("#perf-mode");
      const perfUsersInput = box.querySelector("#perf-users");
      const perfDurationInput = box.querySelector("#perf-duration");

      
      const switchView = (view, title) => {
        mainView.classList.remove("active-view");
        uiTestView.classList.remove("active-view");
        perfTestView.classList.remove("active-view");
        view.classList.add("active-view");
        titleSpan.innerText = title;
      };

      box.querySelector("#go-ui-test").onclick = () => switchView(uiTestView, "UI Testing");
      box.querySelector("#go-perf-test").onclick = () => switchView(perfTestView, "Performance Testing");
      
      box.querySelectorAll(".back-btn").forEach(btn => {
        btn.onclick = () => switchView(mainView, "QA Control Panel");
      });

      
      uiModeSelect.onchange = () => {
        uiTextArea.style.display = uiModeSelect.value === "scenario_test" ? "block" : "none";
      };

      
      box.querySelectorAll(".run-btn").forEach(btn => {
        btn.onclick = (e) => {
          const category = e.target.getAttribute("data-category");
          
          statusDiv.innerText = "⏳ Sending request...";
          statusDiv.style.color = "#ffc107"; 

          
          const payload = {
            url: tabUrl,
            category: category,
            mode: category === "ui_test" ? uiModeSelect.value : perfModeSelect.value,
            scenario_text: category === "ui_test" && uiModeSelect.value === "scenario_test" ? uiTextArea.value : "",
            performance_params: {
              users: category === "performance_test" ? parseInt(perfUsersInput.value || 0) : 0,
              duration: category === "performance_test" ? perfDurationInput.value : ""
            }
          };

          fetch("http://127.0.0.1:8000/server", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          })
          .then(() => {
            statusDiv.innerText = "🚀 Request Sent!";
            statusDiv.style.color = "#28a745";
          })
          .catch(() => {
            statusDiv.innerText = "❌ Connection Error";
            statusDiv.style.color = "#dc3545";
          });
        };
      });

      
      setInterval(() => {
        if (!document.getElementById("qa-box")) return;
        fetch("http://127.0.0.1:8000/status")
          .then(res => res.json())
          .then(data => {
            if (data.step) {
               statusDiv.innerText = `${data.step} - ${data.message}`;
               statusDiv.style.color = data.step === "finished" ? "#28a745" : "#aaa";
            }
          })
          .catch(() => {});
      }, 2000);

      
      let isDragging = false, offset = [0, 0];
      box.onmousedown = (e) => {
        if (["SELECT", "TEXTAREA", "BUTTON", "INPUT"].includes(e.target.tagName)) return;
        if (e.offsetX > box.clientWidth - 15 && e.offsetY > box.clientHeight - 15) return; 

        isDragging = true;
        offset = [box.offsetLeft - e.clientX, box.offsetTop - e.clientY];
        box.style.cursor = "grabbing";
      };

      document.onmousemove = (e) => {
        if (!isDragging) return;
        box.style.left = (e.clientX + offset[0]) + "px";
        box.style.top = (e.clientY + offset[1]) + "px";
      };

      document.onmouseup = () => { 
        isDragging = false; 
        box.style.cursor = "grab"; 
      };

      box.querySelector("#close").onclick = () => box.remove();
    },
    args: [tab.url]
  });
});