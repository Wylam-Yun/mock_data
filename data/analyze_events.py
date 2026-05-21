import json

# 加载事件数据
with open('event_noise_paraphrased.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"总事件数: {len(data['event_logs'])}")

# SOP中告警检测的关键词
# [SOP-EVT-001] 告警检测：配合人分析目标集群未处理告警
# [SOP-EVT-002] 告警检测：配合人查看目标集群 SLA，确认成功率保持 99.99% 以上
# [SOP-EVT-003] 告警检测：配合人查询是否存在 1043006-bill-progress-delay 告警
# [SOP-EVT-004] 告警检测：如存在 1043006-bill-progress-delay 告警，配合人联系后台 oncall 确认
# [SOP-EVT-005] 告警检测验证：配合人完成告警分析，确认未发现影响

# 目标集群
target_cluster = "cn-east-1-bill-cluster-a"

# 关键词列表 - 告警相关
alarm_keywords = ["告警", "alarm", "alert", "1043006-bill-progress-delay", "SLA", "sla"]

# 搜索告警相关事件
print("\n===== 告警相关事件搜索 =====")
alarm_events = []
for event in data['event_logs']:
    event_text = json.dumps(event, ensure_ascii=False)
    # 检查是否包含告警相关关键词
    for keyword in alarm_keywords:
        if keyword.lower() in event_text.lower():
            alarm_events.append(event)
            break

print(f"找到 {len(alarm_events)} 条告警相关事件")

# 搜索特定SOP事件ID对应的活动
# SOP-EVT-001: 配合人分析目标集群未处理告警
print("\n----- SOP-EVT-001: 配合人分析目标集群未处理告警 -----")
evt_001_candidates = []
for event in data['event_logs']:
    event_name = event.get('event_name', '')
    event_type = event.get('event_type', '')
    role = event.get('role', '')
    platform = event.get('platform', '')
    
    # 配合人查询告警/检查告警规则
    if role == '配合人' and ('查询告警' in event_name or '检查告警规则' in event_name):
        evt_001_candidates.append(event)

print(f"找到 {len(evt_001_candidates)} 条SOP-EVT-001候选事件")
for evt in evt_001_candidates[:5]:
    print(f"  [{evt['log_id']}] {evt['event_time']} | {evt['actor']} | {evt['platform']} | {evt['event_name']}")
    if 'params' in evt:
        print(f"    参数: {json.dumps(evt['params'], ensure_ascii=False)}")
    if 'detection_log' in evt:
        print(f"    日志: {evt['detection_log'][:100]}")

# SOP-EVT-002: 配合人查看目标集群 SLA，确认成功率保持 99.99% 以上
print("\n----- SOP-EVT-002: 配合人查看目标集群 SLA -----")
evt_002_candidates = []
for event in data['event_logs']:
    event_name = event.get('event_name', '')
    role = event.get('role', '')
    platform = event.get('platform', '')
    event_text = json.dumps(event, ensure_ascii=False)
    
    if role == '配合人' and ('SLA' in event_text.upper() or 'sla' in platform.lower() or '成功' in event_text and '率' in event_text):
        evt_002_candidates.append(event)

print(f"找到 {len(evt_002_candidates)} 条SOP-EVT-002候选事件")
for evt in evt_002_candidates[:5]:
    print(f"  [{evt['log_id']}] {evt['event_time']} | {evt['actor']} | {evt['platform']} | {evt['event_name']}")
    if 'params' in evt:
        print(f"    参数: {json.dumps(evt['params'], ensure_ascii=False)}")
    if 'detection_log' in evt:
        print(f"    日志: {evt['detection_log'][:100]}")

# SOP-EVT-003: 配合人查询是否存在 1043006-bill-progress-delay 告警
print("\n----- SOP-EVT-003: 查询是否存在 1043006-bill-progress-delay 告警 -----")
evt_003_candidates = []
for event in data['event_logs']:
    event_text = json.dumps(event, ensure_ascii=False)
    role = event.get('role', '')
    
    if role == '配合人' and '1043006' in event_text:
        evt_003_candidates.append(event)

print(f"找到 {len(evt_003_candidates)} 条SOP-EVT-003候选事件")
for evt in evt_003_candidates[:5]:
    print(f"  [{evt['log_id']}] {evt['event_time']} | {evt['actor']} | {evt['platform']} | {evt['event_name']}")
    if 'params' in evt:
        print(f"    参数: {json.dumps(evt['params'], ensure_ascii=False)}")
    if 'detection_log' in evt:
        print(f"    日志: {evt['detection_log'][:100]}")

# 搜索目标集群相关的告警查询
print("\n----- 与目标集群相关的告警查询 -----")
target_alarm_events = []
for event in data['event_logs']:
    event_text = json.dumps(event, ensure_ascii=False)
    role = event.get('role', '')
    event_name = event.get('event_name', '')
    
    if role == '配合人' and target_cluster in event_text and ('告警' in event_name or '告警' in event_text or 'alarm' in event_text.lower()):
        target_alarm_events.append(event)

print(f"找到 {len(target_alarm_events)} 条目标集群告警相关事件")
for evt in target_alarm_events:
    print(f"  [{evt['log_id']}] {evt['event_time']} | {evt['actor']} | {evt['platform']} | {evt['event_name']}")
    if 'params' in evt:
        print(f"    参数: {json.dumps(evt['params'], ensure_ascii=False)}")
    if 'detection_log' in evt:
        print(f"    日志: {evt['detection_log']}")

# 搜索配合人的所有告警操作
print("\n----- 配合人的所有告警操作汇总 -----")
cooperator_alarm_events = []
for event in data['event_logs']:
    role = event.get('role', '')
    event_name = event.get('event_name', '')
    platform = event.get('platform', '')
    
    if role == '配合人' and ('告警' in event_name or 'alarm' in platform.lower() or 'monitor' in platform.lower()):
        cooperator_alarm_events.append(event)

print(f"找到 {len(cooperator_alarm_events)} 条配合人告警相关事件")
for evt in cooperator_alarm_events:
    print(f"  [{evt['log_id']}] {evt['event_time']} | {evt['actor']} | {evt['platform']} | {evt['event_name']} | {evt['event_type']}")
