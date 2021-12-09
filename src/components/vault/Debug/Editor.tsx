import React, { useEffect } from 'react';
import * as CodeMirror from 'codemirror';
import 'codemirror/mode/python/python';
import './Editor.scss';

const Editor: React.FC = (props) => {

    const { sourceCode, sessionId, selectedFile, threadId } = props;

    console.log('sourceCode: ', sourceCode);
   
    let pausedThreads = new Map;
    var selectedThread = 0;
    // var selectedFile = "";
    var selectedLine = null;
    var editor = null;
    var refreshTimer = null;
    var breakpoints = [];

    useEffect(() => {
        var initValue = sourceCode;

        var myTextArea = document.getElementById("code");
        var editor = CodeMirror.fromTextArea(myTextArea, {
            mode: {
                name: "python",
                version: 3,
                extra_keywords: ["load"],
            },
            lineNumbers: true,
            indentUnit: 4,
            readOnly: true,
            gutters: [
                "CodeMirror-linenumbers",
                "breakpoints"
            ],
        });
        editor.setOption("value", initValue);
        editor.on("gutterClick", breakpointClick);

        editor.addLineClass(6, "background", "styled-background");
        editor.addLineClass(10, "background", "styled-background2");
        editor.addLineClass(14, "background", "foo-background");
        document.getElementById("default-tab").click();
        init(editor);
        listenEvents();
    }, []);

    function init(ed) {
        editor = ed;
    }
      
    function unselectThread() {
        if (selectedThread == 0) {
            return;
        }
        document.getElementById("status").textContent = "Running";
    }

    function loadFile(file, line, highlight) {
        if (highlight && selectedLine != null) {
          editor.removeLineClass(selectedLine - 1, "background", "selected-line");
        }
      
        var updateUI = function() {
          var thread = pausedThreads.get(selectedThread);
      
          if (highlight) {
            editor.addLineClass(line - 1, "background", "selected-line");
            selectedLine = line;
          }
          editor.scrollIntoView({line: line - 1}, 100);
      
          breakpoints.forEach(bp => {
            if (bp.location.path === file) {
              addBreakpointDiv(bp.location.lineNumber - 1);
            }
          });
        };
      
        var updateContent = function(content, filename) {
          selectedFile = file;
          editor.setValue(content);
      
          // file name at the top
          var marker = document.createElement("div");
          marker.innerHTML = filename;
          editor.addLineWidget(0, marker, {above: true, className: "line-widget"});
        };
      
        if (selectedFile != file) {
          var xhr = new XMLHttpRequest();
          xhr.open('GET', '/file' + file);
      
          xhr.onreadystatechange = function () {
            var DONE = 4; // readyState 4 means the request is done.
            var OK = 200; // status 200 is a successful return.
      
            if (xhr.readyState === DONE) {
              if (xhr.status === OK) {
                updateContent(xhr.responseText, file);
                updateUI();
              } else {
            console.log('Error: ' + xhr.status);
              }
            }
          };
      
          xhr.send(null);
        } else {
          updateUI();
        }
    }

    function selectThread(id) {
        selectedThread = id;
        sendRequest({listFrames: {threadId: id}});
      
        var thread = pausedThreads.get(id);
        loadFile(thread.location.path, thread.location.lineNumber, true);
        document.getElementById("status").textContent = "Debugging " + thread.name;
    }

    function sendRequest(data) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/request");
        xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
        xhr.send(JSON.stringify(data));
    }

    function refreshThreadList() {
        var tbody = document.getElementById('threads-body');
        tbody.innerHTML = '';
      
        // Instead of recreating the DOM immediately, we wait a bit in case there are
        // other events updating pausedThreads.
        clearTimeout(refreshTimer);
        refreshTimer = setTimeout(function() {
          pausedThreads.forEach((thread, id) => {
            var row = tbody.insertRow(0);
            var button = document.createElement("a");
            button.textContent = thread.id;
            button.onclick = function() { selectThread(thread.id); };
            button.href = "#";
      
            row.insertCell().appendChild(button);
            row.insertCell().textContent = thread.location.path;
            row.insertCell().textContent = thread.location.lineNumber;
            row.insertCell().textContent = thread.name;
            row.insertCell().textContent = thread.pauseReason;
          })
        }, 5);
    }

    function threadPausedEvent(th) {
        pausedThreads.set(th.id, th);
        refreshThreadList();
      
        // If another paused thread is selected, don't update the view.
        if (selectedThread == th.id || !pausedThreads.has(selectedThread)) {
          selectThread(th.id);
        }
    }

    function listFramesEvent(frames) {
        // Update the call stack
        var tbody = document.getElementById('stack-body');
        tbody.innerHTML = '';
      
        frames.forEach(frame => {
          var row = tbody.insertRow();
          var button = document.createElement("a");
          button.textContent = frame.functionName;
          button.onclick = function() { loadFile(frame.location.path, frame.location.lineNumber, true); };
          button.href = "#";
      
          row.insertCell().appendChild(button);
          row.insertCell().textContent = frame.location.path;
          row.insertCell().textContent = frame.location.lineNumber;
        });
      
        // Update the locals
        tbody = document.getElementById('locals-body');
        tbody.innerHTML = '';
      
        frame = frames[0];
        frame.scope.forEach(scope => {
          if (scope.binding) {
            scope.binding.forEach(binding => {
              var row = tbody.insertRow();
              row.insertCell().textContent = binding.label;
              row.insertCell().textContent = binding.description;
              row.insertCell().textContent = binding.type;
            });
          }
        });
    }

    const sendBreakpoints = async (breakpoints) => {
        const url = new URL(`http://localhost:8089/debug/${sessionId}/breakpoints`);
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json;charset=utf-8'
            },
            body: JSON.stringify({
                breakpoints
            })
        });

        const result = await response.json();

        if (result.error) {
            console.log(result.error.message);
        }

        console.log('sendBreakpoints: ', result);
    };

    function setBreakpointsEvent(e) {
        if (e == null) {
          return;
        }
      
        breakpoints = e;
        console.log("bps", e);
        // sendRequest({setBreakpoints: {breakpoint: e}});
        sendBreakpoints(e);
      
        var tbody = document.getElementById('breakpoints-body');
        tbody.innerHTML = '';
      
        breakpoints.forEach(bp => {
          var row = tbody.insertRow();
          var button = document.createElement("a");
          button.textContent = bp.location.path;
          button.onclick = function() { loadFile(bp.location.path, bp.location.lineNumber, false); };
          button.href = "#";
      
          row.insertCell().appendChild(button);
          row.insertCell().textContent = bp.location.lineNumber;
          row.insertCell(); // TODO(laurentlb): Conditional breakpoints.
        });
    }

    function handleEvent(e) {
        console.log('handleEvent: ', e);
        if (e.hasOwnProperty("threadPaused")) {
          threadPausedEvent(e.threadPaused.thread);
        } else if (e.hasOwnProperty("listFrames")) {
          listFramesEvent(e.listFrames.frame);
        } else if (e.hasOwnProperty("setBreakpoints")) {
          setBreakpointsEvent(e.setBreakpoints.breakpoint);
        } else {
          console.log("other", e);
        }
        // else if (Array.isArray(e)) {
        //   breakpoints = e;
        // }
    }

    function listenEvents() {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/updates');
      
        // Track the state changes of the request.
        xhr.onreadystatechange = function () {
          var DONE = 4; // readyState 4 means the request is done.
          var OK = 200; // status 200 is a successful return.
      
          if (xhr.readyState === DONE) {
            if (xhr.status === OK) {
              handleEvent(JSON.parse(xhr.responseText));
              return listenEvents();
            } else {
          console.log('Error: ' + xhr.status);
              document.getElementById("status").textContent = "Connection closed.";
            }
          }
        };
      
        xhr.send(null);
    }

    const continueThread = async (stepping) => {
        const url = new URL(`http://localhost:8089/debug/${sessionId}/threads/${threadId}/continue`);
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json;charset=utf-8'
            },
            body: JSON.stringify({
                stepping
            })
        });

        const result = await response.json();

        if (result.error) {
            console.log(result.error.message);
        }

        console.log('continueThread: ', result);
    };

    function stepButton(stepping) {
        if (stepping == null) { // resume all
          pausedThreads.clear();
          selectedThread = 0;
        } else {
          pausedThreads.delete(selectedThread);
        }
        
        continueThread(stepping);
        
        // sendRequest({
        //   continueExecution: {
        //     threadId: selectedThread,
        //     stepping: stepping
        // }});

        if (selectedLine != null) {
          editor.removeLineClass(selectedLine - 1, "background", "selected-line");
        }
        refreshThreadList();
    }

    function stopAllButton() {
        sendRequest({pauseThread: {threadId: 0}});
    }

    function addBreakpointDiv(n) {
        var info = editor.lineInfo(n);
        if (info.gutterMarkers) {
          return;
        }
        var marker = document.createElement("div");
        marker.classList.add("breakpoint");
        marker.innerHTML = "●";
        editor.setGutterMarker(n, "breakpoints", marker);
    }
      
    function breakpointClick(cm, n) {
        console.log('breakpointClick: ');
        var info = cm.lineInfo(n);
        console.log('breakpointClick: ');
        if (info.gutterMarkers) {
          breakpoints = breakpoints.filter(
              bp => bp.location.path != selectedFile || bp.location.line_number != n + 1);
          sendRequest({setBreakpoints: {breakpoint: breakpoints}});
          editor.setGutterMarker(n, "breakpoints", null);
        } else {
          var loc = {location: {path: selectedFile, line_number: n + 1}};
          breakpoints.push(loc);
          addBreakpointDiv(n);
        }
        console.log('breakpointClick: ', breakpoints)
        setBreakpointsEvent(breakpoints);
    }

    function openTab(evt, tabName) {
        var i, tabcontent, tablinks;
  
        // Hide all the tabs.
        tabcontent = document.getElementsByClassName("tab-content");
        for (var i = 0; i < tabcontent.length; i++) {
            tabcontent[i].style.display = "none";
        }
  
        // Remove active from all the tab names.
        tablinks = document.getElementsByClassName("tablinks");
        for (var i = 0; i < tablinks.length; i++) {
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }
  
        // Show the content.
        document.getElementById(tabName).style.display = "block";
        evt.currentTarget.className += " active";
    }

    return (
        <div>
            <div className="status" id="status">Debugging somefile.bzl</div>
            <div className="tab">
                <button className="tablinks" onClick={() => stepButton('NONE')}>Continue</button>
                <button className="tablinks" onClick={() => stepButton('INTO')}>Step into</button>
                <button className="tablinks" onClick={() => stepButton('OVER')}>Step over</button>
                <button className="tablinks" onClick={() => stepButton('OUT')}>Step out</button>
            </div>

            <textarea id="code">
            </textarea>

            <div style={{ overflowX: 'auto' }}>

                <div className="tab">
                    <button className="tablinks" onClick={() => openTab(event, 'locals-tab')}>Locals</button>
                    <button className="tablinks" onClick={() => openTab(event, 'watch-tab')}>Watch</button>
                    <button className="tablinks" onClick={() => openTab(event, 'stack-tab')}>Call Stack</button>
                    <button className="tablinks" onClick={() => openTab(event, 'breakpoints-tab')} id="default-tab">Breakpoints</button>
                    <button className="tablinks" onClick={() => openTab(event, 'threads-tab')}>Paused Threads</button>
                </div>

                <div id="locals-tab" className="tab-content">

                    <table width="100%">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Value</th>
                                <th>Type</th>
                            </tr>
                        </thead>
                        <tbody id="locals-body">
                            <tr>
                                <td>foo</td>
                                <td>12</td>
                                <td>int</td>
                            </tr>
                            <tr>
                                <td>bar</td>
                                <td>"str"</td>
                                <td>str</td>
                            </tr>
                            <tr>
                                <td>x</td>
                                <td>5</td>
                                <td>int</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div id="watch-tab" className="tab-content">
                    <p>Not implemented.</p>
                </div>

                <div id="stack-tab" className="tab-content">

                    <table width="100%">
                        <thead>
                            <tr>
                                <th>Function</th>
                                <th>Path</th>
                                <th>Line</th>
                            </tr>
                        </thead>
                        <tbody id="stack-body">
                            <tr>
                                <td>hello</td>
                            </tr>
                        </tbody>
                    </table>

                </div>

                <div id="breakpoints-tab" className="tab-content">

                    <table width="100%">
                        <thead>
                            <tr>
                                <th>Path</th>
                                <th>Line</th>
                                <th>Condition</th>
                            </tr>
                        </thead>
                        <tbody id="breakpoints-body">
                        </tbody>
                    </table>

                </div>

                <div id="threads-tab" className="tab-content">

                    <table width="100%">
                        <thead>
                            <tr>
                                <th>Id</th>
                                <th>Path</th>
                                <th>Line</th>
                                <th>Name</th>
                                <th>Reason</th>
                            </tr>
                        </thead>
                        <tbody id="threads-body">
                        </tbody>
                    </table>

                    <button className="tablinks" onClick={stopAllButton}>Stop All</button>
                    <button className="tablinks" onClick={() => stepButton(null)}>Resume all</button>
                </div>

            </div>
        </div>
    );
};

export default Editor;
