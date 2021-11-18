import React, { useEffect } from 'react';
import './Editor.scss';

const Editor: React.FC = () => {
   
    let pausedThreads = new Map;
    var selectedThread = 0;
    var selectedFile = "";
    var selectedLine = null;
    var editor = null;
    var refreshTimer = null;
    var breakpoints = [];

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

    function stepButton(stepping) {
        if (stepping == null) { // resume all
          pausedThreads.clear();
          selectedThread = 0;
        } else {
          pausedThreads.delete(selectedThread);
        }
      
        sendRequest({
          continueExecution: {
            threadId: selectedThread,
            stepping: stepping
        }});
        if (selectedLine != null) {
          editor.removeLineClass(selectedLine - 1, "background", "selected-line");
        }
        refreshThreadList();
      }

    function stopAllButton() {
        sendRequest({pauseThread: {threadId: 0}});
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
            <div className="tab">
                <button className="tablinks" onClick={() => stepButton('NONE')}>Continue</button>
                <button className="tablinks" onClick={() => stepButton('INTO')}>Step into</button>
                <button className="tablinks" onClick={() => stepButton('OVER')}>Step over</button>
                <button className="tablinks" onClick={() => stepButton('OUT')}>Step out</button>
            </div>

            <textarea id="code"></textarea>

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
