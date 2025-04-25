document.addEventListener('DOMContentLoaded', function() {
    // 页面加载完成后执行
    // 侧边栏导航激活状态切换
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    const settingsSections = document.querySelectorAll('.settings-section');
    
    // 初始化Bootstrap提示框
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化警告提示框
    const alertPlaceholder = document.getElementById('alertContainer');
    
    // 处理JSON检查区域的显示/隐藏
    const enableJsonCheck = document.getElementById('enableJsonCheck');
    const jsonCheckSection = document.getElementById('jsonCheckSection');
    
    // 初始化时设置JSON检查区域状态
    if (jsonCheckSection && enableJsonCheck) {
        if (!enableJsonCheck.checked) {
            // 默认隐藏JSON检查区域
            jsonCheckSection.style.display = 'none';
        }
        
        // 添加复选框变化事件处理
        enableJsonCheck.addEventListener('change', function() {
            if (this.checked) {
                jsonCheckSection.style.display = 'block';
            } else {
                jsonCheckSection.style.display = 'none';
                // 清空JSON检查字段
                document.getElementById('endpointJsonCheckPath').value = '';
                document.getElementById('endpointJsonCheckValue').value = '';
            }
        });
    }
    
    // 显示警告提示框函数
    function showAlert(message, type = 'success') {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="关闭"></button>
            </div>
        `;
        
        alertPlaceholder.append(wrapper);
        
        // 5秒后自动关闭
        setTimeout(() => {
            const alert = wrapper.querySelector('.alert');
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    }
    
    // 切换设置部分显示
    function showSettingsSection(sectionId) {
        settingsSections.forEach(section => {
            section.classList.add('d-none');
        });
        
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.classList.remove('d-none');
            // 更新URL哈希，便于刷新保持相同页面
            window.location.hash = sectionId;
        }
        
        // 更新导航激活状态
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-section') === sectionId) {
                link.classList.add('active');
            }
        });
    }
    
    // 监听侧边栏点击事件
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const sectionId = this.getAttribute('data-section');
            showSettingsSection(sectionId);
        });
    });
    
    // 如果存在URL哈希，显示对应部分
    if (window.location.hash) {
        const sectionId = window.location.hash.substring(1);
        showSettingsSection(sectionId);
    } else {
        // 默认显示常规设置
        showSettingsSection('generalSettings');
    }
    
    // 折叠侧边栏
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('active');
            document.querySelector('.content').classList.toggle('active');
        });
    }
    
    // 处理表单提交
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formId = this.id;
            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            
            // 禁用提交按钮并显示加载状态
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 保存中...';
            
            // 转换为JSON对象
            const jsonData = {};
            formData.forEach((value, key) => {
                // 处理复选框
                if (key.endsWith('[]')) {
                    const actualKey = key.slice(0, -2);
                    if (!jsonData[actualKey]) {
                        jsonData[actualKey] = [];
                    }
                    jsonData[actualKey].push(value);
                } else {
                    jsonData[key] = value;
                }
            });
            
            // 发送API请求
            fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    section: formId,
                    data: jsonData
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    showAlert(data.message || '设置已成功保存！', 'success');
                    // 重新加载配置
                    setTimeout(() => {
                        loadConfig();
                    }, 500);
                } else {
                    showAlert(data.message || '保存设置时出错', 'danger');
                }
            })
            .catch(error => {
                console.error('提交表单错误:', error);
                showAlert('保存设置时出错: ' + error.message, 'danger');
            })
            .finally(() => {
                // 恢复按钮状态
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            });
        });
    });
    
    // 处理端点删除
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-endpoint') || e.target.classList.contains('btn-delete-endpoint')) {
            e.preventDefault();
            const endpointId = e.target.dataset.id;
            
            if (confirm('确定要删除这个端点吗？')) {
                fetch(`/api/endpoints/${endpointId}`, {
                    method: 'DELETE',
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // 从DOM中移除元素
                        const endpointItem = e.target.closest('.endpoint-item');
                        const tableRow = e.target.closest('tr');
                        
                        if (endpointItem) {
                            endpointItem.remove();
                        }
                        
                        if (tableRow) {
                            tableRow.remove();
                        }
                        
                        showAlert(data.message || '端点已成功删除！', 'success');
                    } else {
                        showAlert(data.message || '删除端点时出错', 'danger');
                    }
                })
                .catch(error => {
                    console.error('删除端点错误:', error);
                    showAlert('删除端点时出错: ' + error.message, 'danger');
                });
            }
        }
    });
    
    // 处理端点编辑
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('edit-endpoint') || e.target.classList.contains('btn-edit-endpoint')) {
            e.preventDefault();
            const endpointId = e.target.dataset.id;
            
            // 获取端点数据
            fetch(`/api/endpoints/${endpointId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP错误: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // 确保data是一个有效的端点对象
                    const endpoint = data.hasOwnProperty('status') && data.status === 'error' ? null : data;
                    
                    if (!endpoint) {
                        showAlert('未找到端点数据', 'danger');
                        return;
                    }
                    
                    console.log('编辑端点数据:', endpoint); // 调试信息
                    
                    // 确保端点有ID
                    if (!endpoint.id) {
                        endpoint.id = endpoint.name;
                    }
                    
                    // 直接使用editEndpoint函数处理编辑逻辑，确保所有字段都能正确加载
                    editEndpoint(endpoint);
                })
                .catch(error => {
                    console.error('获取端点数据错误:', error);
                    showAlert(`获取端点数据时出错: ${error.message}`, 'danger');
                });
        }
    });
    
    // 处理添加端点模态框
    const addEndpointBtn = document.querySelector('.btn-add-endpoint');
    const addEndpointModal = document.getElementById('addEndpointModal');
    
    if (addEndpointBtn && addEndpointModal) {
        // 显示模态框时重置表单
        addEndpointBtn.addEventListener('click', function() {
            // 重置表单
            const form = document.getElementById('addEndpointForm');
            if (form) {
                form.reset();
                // 清除ID字段
                document.getElementById('endpointId').value = '';
                // 更改模态框标题
                document.getElementById('modalTitle').textContent = '添加新端点';
            }
            
            // 确保JSON检查区域初始状态正确
            const enableJsonCheck = document.getElementById('enableJsonCheck');
            const jsonCheckSection = document.getElementById('jsonCheckSection');
            
            if (enableJsonCheck && jsonCheckSection) {
                enableJsonCheck.checked = false;
                jsonCheckSection.style.display = 'none';
            }
        });
    }
    
    // 添加端点表单提交
    const addEndpointForm = document.getElementById('addEndpointForm');
    if (addEndpointForm) {
        addEndpointForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveEndpoint();
        });
    }
    
    // 导入配置处理
    const importConfigForm = document.getElementById('importConfigForm');
    if (importConfigForm) {
        importConfigForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const fileInput = document.getElementById('configFile');
            
            if (fileInput.files.length === 0) {
                showAlert('请选择配置文件', 'warning');
                return;
            }
            
            fetch('/api/import-config', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 关闭模态框
                    const modal = bootstrap.Modal.getInstance(document.getElementById('importConfigModal'));
                    modal.hide();
                    
                    showAlert('配置已成功导入！刷新页面以查看更改。', 'success');
                    
                    // 3秒后刷新页面
                    setTimeout(() => {
                        location.reload();
                    }, 3000);
                } else {
                    showAlert('导入配置时出错: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('导入配置错误:', error);
                showAlert('导入配置时出错: ' + error.message, 'danger');
            });
        });
    }
    
    // 导出配置处理
    const exportConfigBtn = document.getElementById('exportConfigBtn');
    if (exportConfigBtn) {
        exportConfigBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            window.location.href = '/api/config/export';
        });
    }
    
    // 测试通知处理
    const testNotificationBtn = document.getElementById('testNotificationBtn');
    if (testNotificationBtn) {
        testNotificationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const originalText = testNotificationBtn.textContent;
            testNotificationBtn.disabled = true;
            testNotificationBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 发送中...';
            
            fetch('/api/notifications/test', {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showAlert('测试通知已发送！', 'success');
                } else {
                    showAlert('发送测试通知时出错: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('测试通知错误:', error);
                showAlert('发送测试通知时出错: ' + error.message, 'danger');
            })
            .finally(() => {
                testNotificationBtn.disabled = false;
                testNotificationBtn.textContent = originalText;
            });
        });
    }

    // 加载配置
    function loadConfig() {
        // 加载常规设置
        fetch('/api/config/general')
            .then(response => response.json())
            .then(data => {
                document.getElementById('appName').value = data.app_name || '';
                document.getElementById('loggingLevel').value = data.logging_level || 'info';
                document.getElementById('checkInterval').value = data.check_interval || 60;
            })
            .catch(error => {
                console.error('加载常规设置失败:', error);
                showAlert('加载常规设置失败', 'danger');
            });

        // 加载通知设置
        fetch('/api/config/notifications')
            .then(response => response.json())
            .then(data => {
                document.getElementById('enableEmailNotifications').checked = data.email_enabled || false;
                document.getElementById('enableWebhookNotifications').checked = data.webhook_enabled || false;
                document.getElementById('enableTelegramNotifications').checked = data.telegram_enabled || false;
                document.getElementById('notifyOnStatus').value = data.notify_on_status || 'error';
            })
            .catch(error => {
                console.error('加载通知设置失败:', error);
                showAlert('加载通知设置失败', 'danger');
            });

        // 加载邮件设置
        fetch('/api/config/email')
            .then(response => response.json())
            .then(data => {
                document.getElementById('smtpServer').value = data.smtp_server || '';
                document.getElementById('smtpPort').value = data.smtp_port || 587;
                document.getElementById('smtpUsername').value = data.username || '';
                document.getElementById('smtpPassword').value = data.password || '';
                document.getElementById('emailFrom').value = data.sender || '';
                
                // 处理recipients可能是字符串的情况
                const recipients = data.recipients || '';
                if (Array.isArray(recipients)) {
                    document.getElementById('emailTo').value = recipients.join('\n');
                } else {
                    document.getElementById('emailTo').value = recipients;
                }
            })
            .catch(error => {
                console.error('加载邮件设置失败:', error);
                showAlert('加载邮件设置失败', 'danger');
            });

        // 加载Webhook设置
        fetch('/api/config/webhook')
            .then(response => response.json())
            .then(data => {
                document.getElementById('webhookUrl').value = data.url || '';
                document.getElementById('webhookMethod').value = data.method || 'POST';
                document.getElementById('webhookHeaders').value = JSON.stringify(data.headers || {}, null, 2);
            })
            .catch(error => {
                console.error('加载Webhook设置失败:', error);
                showAlert('加载Webhook设置失败', 'danger');
            });

        // 加载Telegram设置
        fetch('/api/config/telegram')
            .then(response => response.json())
            .then(data => {
                document.getElementById('telegramToken').value = data.token || '';
                
                // 处理chat_ids可能是字符串的情况
                const chatIds = data.chat_ids || '';
                if (Array.isArray(chatIds)) {
                    document.getElementById('telegramChatIds').value = chatIds.join('\n');
                } else {
                    document.getElementById('telegramChatIds').value = chatIds;
                }
            })
            .catch(error => {
                console.error('加载Telegram设置失败:', error);
                showAlert('加载Telegram设置失败', 'danger');
            });

        // 加载端点配置
        fetch('/api/endpoints')
            .then(response => response.json())
            .then(endpoints => {
                console.log("加载端点数据:", endpoints); // 调试信息
                
                // 更新端点表格
                const endpointsTable = document.getElementById('endpointsTable');
                if (endpointsTable) {
                    const tbody = endpointsTable.querySelector('tbody');
                    tbody.innerHTML = '';
                    
                    if (endpoints.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" class="text-center">暂无端点配置</td></tr>';
                    } else {
                        endpoints.forEach(endpoint => {
                            // 确保每个端点都有ID
                            if (!endpoint.id) {
                                endpoint.id = endpoint.name || `endpoint-${Date.now()}`;
                            }
                            
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${endpoint.name || '未命名'}</td>
                                <td>${endpoint.url || '未设置'}</td>
                                <td>
                                    <span class="status-indicator ${endpoint.status === 'ok' ? 'status-ok' : 'status-error'}"></span>
                                    ${endpoint.status === 'ok' ? '正常' : '异常'}
                                </td>
                                <td>${endpoint.last_check || '未检查'}</td>
                                <td>
                                    <div class="btn-group">
                                        <button class="btn btn-sm btn-primary btn-edit-endpoint" data-id="${endpoint.id}">
                                            <i class="bi bi-pencil"></i>
                                        </button>
                                        <button class="btn btn-sm btn-danger btn-delete-endpoint" data-id="${endpoint.id}">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </div>
                                </td>
                            `;
                            tbody.appendChild(row);
                        });
                    }
                }
                
                // 更新端点卡片视图
                const endpointsContainer = document.getElementById('endpointsContainer');
                if (endpointsContainer) {
                    endpointsContainer.innerHTML = '';
                    
                    if (endpoints.length === 0) {
                        endpointsContainer.innerHTML = '<div class="alert alert-info">暂无端点配置</div>';
                    } else {
                        const row = document.createElement('div');
                        row.className = 'row';
                        
                        endpoints.forEach(endpoint => {
                            // 确保每个端点都有ID
                            if (!endpoint.id) {
                                endpoint.id = endpoint.name || `endpoint-${Date.now()}`;
                            }
                            
                            const col = document.createElement('div');
                            col.className = 'col-md-4 mb-3';
                            col.appendChild(createEndpointElement(endpoint));
                            row.appendChild(col);
                        });
                        
                        endpointsContainer.appendChild(row);
                    }
                }
            })
            .catch(error => {
                console.error('加载端点配置失败:', error);
                // 显示错误提示
                showAlert('加载端点配置失败: ' + error.message, 'danger');
            });
    }

    // 加载端点列表 - 供内部使用和API响应后刷新用
    function loadEndpoints() {
        // 直接调用loadConfig来加载所有配置，包括端点
        loadConfig();
    }

    // 创建端点元素
    function createEndpointElement(endpoint) {
        // 确保端点有ID，如果没有，使用name作为ID
        if (!endpoint.id) {
            endpoint.id = endpoint.name || `endpoint-${Date.now()}`;
        }
        
        const div = document.createElement('div');
        div.className = 'endpoint-item card mb-3';
        div.innerHTML = `
            <div class="card-body">
                <h5 class="card-title">${endpoint.name || '未命名端点'}</h5>
                <p class="card-text">
                    <strong>URL:</strong> ${endpoint.url || '未设置'}<br>
                    <strong>类型:</strong> ${endpoint.type || 'GET'}<br>
                    <strong>超时:</strong> ${endpoint.timeout || 30}秒<br>
                    <strong>状态:</strong> <span class="badge bg-${endpoint.enabled ? 'success' : 'danger'}">${endpoint.enabled ? '启用' : '禁用'}</span>
                </p>
                <div class="btn-group">
                    <button class="btn btn-sm btn-primary edit-endpoint" data-id="${endpoint.id}">编辑</button>
                    <button class="btn btn-sm btn-danger delete-endpoint" data-id="${endpoint.id}">删除</button>
                </div>
            </div>
        `;
        return div;
    }

    // 加载配置
    loadConfig();

    function editEndpoint(endpoint) {
        console.log("开始设置编辑表单", endpoint);
        
        // 设置基本表单字段值
        $("#endpointId").val(endpoint.id);
        $("#endpointName").val(endpoint.name);
        $("#endpointUrl").val(endpoint.url);
        
        // 处理请求方法
        const methodField = document.getElementById('endpointMethod');
        if (methodField) {
            const methodValue = endpoint.method || 'GET';
            
            // 确保选择的值在选项列表中存在
            let optionExists = false;
            for (let i = 0; i < methodField.options.length; i++) {
                if (methodField.options[i].value === methodValue) {
                    optionExists = true;
                    break;
                }
            }
            
            if (optionExists) {
                methodField.value = methodValue;
            } else {
                // 如果值不在选项列表中，创建一个新选项
                const option = document.createElement('option');
                option.value = methodValue;
                option.text = methodValue;
                methodField.add(option);
                methodField.value = methodValue;
            }
        }
        
        // 设置检查间隔
        const intervalMinutes = endpoint.interval_minutes || 5;
        $("#endpointInterval").val(intervalMinutes);
        
        // 设置启用状态
        $("#endpointEnabled").prop('checked', endpoint.enabled !== false);
        
        // 设置高级配置字段
        $("#endpointExpectedStatus").val(endpoint.expected_status || 200);
        
        // 设置期望内容
        if (endpoint.expected_content !== undefined && endpoint.expected_content !== null) {
            $("#endpointExpectedContent").val(endpoint.expected_content);
            console.log("设置期望内容:", endpoint.expected_content);
        } else {
            $("#endpointExpectedContent").val('');
        }
        
        // 设置headers (如果是字符串则直接使用，否则转为JSON字符串)
        if (endpoint.headers) {
            if (typeof endpoint.headers === 'string') {
                $("#endpointHeaders").val(endpoint.headers);
            } else {
                $("#endpointHeaders").val(JSON.stringify(endpoint.headers, null, 2));
            }
            console.log("设置请求头:", endpoint.headers);
        } else {
            $("#endpointHeaders").val('');
        }
        
        // 设置body
        if (endpoint.body) {
            if (typeof endpoint.body === 'string') {
                $("#endpointBody").val(endpoint.body);
            } else {
                $("#endpointBody").val(JSON.stringify(endpoint.body, null, 2));
            }
            console.log("设置请求体:", endpoint.body);
        } else {
            $("#endpointBody").val('');
        }
        
        // 设置JSON检查字段 - 注意使用expected_value而非value
        if (endpoint.json_check) {
            $("#endpointJsonCheckPath").val(endpoint.json_check.path || '');
            $("#endpointJsonCheckValue").val(endpoint.json_check.expected_value || '');
            console.log("设置JSON检查:", endpoint.json_check);
            
            // 如果存在enable/disable JSON检查的复选框，设置其状态
            if ($("#enableJsonCheck").length) {
                $("#enableJsonCheck").prop('checked', true);
                // 如果有显示/隐藏相关区域的代码，也应该触发
                if (typeof $("#enableJsonCheck").change === 'function') {
                    $("#enableJsonCheck").change();
                }
            }
        } else {
            $("#endpointJsonCheckPath").val('');
            $("#endpointJsonCheckValue").val('');
            
            // 如果存在enable/disable JSON检查的复选框，设置其状态
            if ($("#enableJsonCheck").length) {
                $("#enableJsonCheck").prop('checked', false);
                // 如果有显示/隐藏相关区域的代码，也应该触发
                if (typeof $("#enableJsonCheck").change === 'function') {
                    $("#enableJsonCheck").change();
                }
            }
        }
        
        // 设置模态框标题
        $("#modalTitle").text("编辑端点");
        
        // 显示模态框
        $("#addEndpointModal").modal("show");
        console.log("编辑模态框已显示");
    }

    function saveEndpoint() {
        // 获取表单数据
        const id = $("#endpointId").val();
        const name = $("#endpointName").val();
        const url = $("#endpointUrl").val();
        const method = $("#endpointMethod").val();
        const interval = parseInt($("#endpointInterval").val(), 10);
        const enabled = $("#endpointEnabled").is(":checked");
        
        // 获取高级配置
        const expected_status = parseInt($("#endpointExpectedStatus").val(), 10) || 200;
        const expected_content = $("#endpointExpectedContent").val();
        
        // 获取headers和body，尝试解析JSON
        let headers = {};
        const headersText = $("#endpointHeaders").val().trim();
        if (headersText) {
            try {
                headers = JSON.parse(headersText);
            } catch (e) {
                showAlert("请求头格式不正确，请使用有效的JSON格式", "danger");
                return;
            }
        }
        
        let body = null;
        const bodyText = $("#endpointBody").val().trim();
        if (bodyText) {
            try {
                body = JSON.parse(bodyText);
            } catch (e) {
                showAlert("请求体格式不正确，请使用有效的JSON格式", "danger");
                return;
            }
        }
        
        // 获取JSON检查配置
        let json_check = null;
        const jsonCheckPath = $("#endpointJsonCheckPath").val().trim();
        const jsonCheckValue = $("#endpointJsonCheckValue").val().trim();
        
        // 只有当路径和值都有内容时，才添加JSON检查
        if (jsonCheckPath && jsonCheckValue) {
            json_check = {
                path: jsonCheckPath,
                expected_value: jsonCheckValue  // 注意这里使用expected_value而不是value
            };
            console.log("添加JSON检查:", json_check); // 调试
        }
        
        // 构建端点对象
        const endpoint = {
            id: id || name,  // 确保ID不为null，使用name作为后备
            name,
            url,
            method,
            interval_minutes: interval,
            enabled,
            expected_status,
            expected_content: expected_content || null,
            headers: Object.keys(headers).length > 0 ? headers : null,
            body,
            json_check
        };
        
        console.log("保存端点数据:", endpoint); // 调试信息
        
        // 添加或更新端点
        if (id) {
            // 更新端点
            fetch(`/api/endpoints/${id}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(endpoint),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP错误: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    $("#addEndpointModal").modal("hide");
                    loadConfig();
                    showAlert("端点更新成功", "success");
                } else {
                    showAlert(`更新失败: ${data.message}`, "danger");
                }
            })
            .catch(error => {
                console.error("Error:", error);
                showAlert(`更新端点时发生错误: ${error.message}`, "danger");
            });
        } else {
            // 添加新端点
            fetch("/api/endpoints", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(endpoint),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP错误: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    $("#addEndpointModal").modal("hide");
                    loadConfig();
                    showAlert("端点添加成功", "success");
                } else {
                    showAlert(`添加失败: ${data.message}`, "danger");
                }
            })
            .catch(error => {
                console.error("Error:", error);
                showAlert(`添加端点时发生错误: ${error.message}`, "danger");
            });
        }
    }
});