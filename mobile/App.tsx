import { StatusBar } from 'expo-status-bar'
import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, Alert, FlatList, Modal, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { ApiError, Entry, Handover, Me, Notice, Proj, Task, Week, api, signIn, signOut } from './api'

const C = { bg: '#f5f7fa', ink: '#1c2433', mute: '#5a667a', line: '#e3e8ef', acc: '#2f5bea', ok: '#12805c', warn: '#8a5a00', bad: '#b42318' }
const STATUSES = ['Todo', 'In progress', 'Blocked', 'Done']
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const tone = (s: string) => ({ Done: C.ok, Approved: C.ok, Acknowledged: C.ok, Blocked: C.bad, Rejected: C.bad, Pending: C.warn, Submitted: C.acc, 'In progress': C.acc }[s] ?? C.mute)

function useLoad<T>(path: string) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => { setLoading(true); try { setData(await api<T>(path)); setError('') } catch (e) { setError((e as Error).message) } finally { setLoading(false) } }, [path])
  useEffect(() => { load() }, [load])
  return { data, error, loading, reload: load }
}

const Btn = ({ title, onPress, kind, disabled }: { title: string; onPress: () => void; kind?: 'pri' | 'danger'; disabled?: boolean }) => (
  <Pressable accessibilityRole="button" accessibilityLabel={title} disabled={disabled} onPress={onPress} style={[s.btn, kind === 'pri' && { backgroundColor: C.acc, borderColor: C.acc }, kind === 'danger' && { borderColor: C.bad }, disabled && { opacity: 0.5 }]}>
    <Text style={[s.btnT, kind === 'pri' && { color: '#fff' }, kind === 'danger' && { color: C.bad }]}>{title}</Text>
  </Pressable>
)
const Pill = ({ text }: { text: string }) => <Text style={[s.pill, { color: tone(text), borderColor: tone(text) }]}>{text}</Text>
const Err = ({ msg }: { msg: string }) => (msg ? <Text accessibilityRole="alert" style={s.err}>{msg}</Text> : null)
const Wait = () => <ActivityIndicator style={{ margin: 24 }} color={C.acc} />

// ---------------- sign in ----------------
function Login({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const demo = useLoad<{ password: string; accounts: { name: string; role: string; email: string }[] }>('/api/demo/accounts')
  async function go() { setBusy(true); setErr(''); try { await signIn(email.trim().toLowerCase(), pw); onDone() } catch (e) { setErr((e as Error).message) } finally { setBusy(false) } }
  return (
    <ScrollView contentContainerStyle={{ padding: 18 }} keyboardShouldPersistTaps="handled">
      <Text style={s.h1}>Aadi Project Tracker</Text>
      <Text style={s.sub}>Sign in to see your tasks, time and handovers.</Text>
      <Text style={s.label}>Email</Text>
      <TextInput style={s.input} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" accessibilityLabel="Email" />
      <Text style={s.label}>Password</Text>
      <TextInput style={s.input} value={pw} onChangeText={setPw} secureTextEntry accessibilityLabel="Password" />
      <Err msg={err} />
      <Btn title={busy ? 'Signing in…' : 'Sign in'} kind="pri" onPress={go} disabled={busy || !email || !pw} />
      {demo.data && <View style={s.card}>
        <Text style={s.h2}>Demo accounts</Text>
        <Text style={s.sub}>Illustrative data only. Tap Use, then Sign in.</Text>
        {demo.data.accounts.filter((a) => !a.role.includes('Platform')).map((a) => (
          <View key={a.email} style={s.rowBetween}>
            <View style={{ flex: 1 }}><Text style={{ fontWeight: '600', color: C.ink }}>{a.name}</Text><Text style={s.small}>{a.role}</Text></View>
            <Btn title={`Use ${a.name}`} onPress={() => { setEmail(a.email); setPw(demo.data!.password) }} />
          </View>))}
      </View>}
    </ScrollView>
  )
}

// ---------------- my tasks ----------------
function Tasks() {
  const { data, error, loading, reload } = useLoad<Task[]>('/api/tasks?mine=true')
  const [err, setErr] = useState('')
  async function set(t: Task, status: string) { setErr(''); try { await api(`/api/tasks/${t.id}/status`, { method: 'POST', body: { status } }); reload() } catch (e) { setErr((e as Error).message) } }
  if (loading && !data) return <Wait />
  return (
    <FlatList data={data ?? []} keyExtractor={(t) => String(t.id)} onRefresh={reload} refreshing={loading} contentContainerStyle={{ padding: 14 }}
      ListHeaderComponent={<><Text style={s.h1}>My tasks</Text><Err msg={error || err} /></>}
      ListEmptyComponent={<Text style={s.sub}>No tasks assigned to you.</Text>}
      renderItem={({ item: t }) => (
        <View style={s.card}>
          <View style={s.rowBetween}><Text style={s.title}>{t.title}</Text><Pill text={t.status} /></View>
          <Text style={s.small}>{t.project}{t.sprint ? ` · ${t.sprint}` : ''}</Text>
          <Text style={s.small}>{t.priority} priority · {t.est_hours} h{t.due_date ? ` · due ${t.due_date}` : ''}</Text>
          <View style={s.wrap}>{STATUSES.filter((x) => x !== t.status).map((x) => <Btn key={x} title={x} onPress={() => set(t, x)} />)}</View>
        </View>)} />
  )
}

// ---------------- timesheet ----------------
function Timesheet() {
  const [week, setWeek] = useState(iso(new Date()))
  const { data, error, loading, reload } = useLoad<Week>(`/api/timesheets?week=${week}`)
  const [adding, setAdding] = useState(false)
  const [msg, setMsg] = useState('')
  const shift = (d: number) => { const x = new Date(data!.week_start + 'T00:00:00'); x.setDate(x.getDate() + d); setWeek(iso(x)) }
  async function submit() { setMsg(''); try { const r = await api<{ submitted: number }>('/api/timesheets/submit', { method: 'POST', body: { week } }); setMsg(`${r.submitted} entries submitted for approval.`); reload() } catch (e) { setMsg((e as Error).message) } }
  async function del(e: Entry) { try { await api(`/api/timesheets/${e.id}`, { method: 'DELETE' }); reload() } catch (x) { setMsg((x as Error).message) } }
  if (loading && !data) return <Wait />
  if (!data) return <View style={{ padding: 14 }}><Err msg={error} /></View>
  return (
    <View style={{ flex: 1 }}>
      <FlatList data={data.entries} keyExtractor={(e) => String(e.id)} contentContainerStyle={{ padding: 14 }} onRefresh={reload} refreshing={loading}
        ListHeaderComponent={<>
          <Text style={s.h1}>Timesheet</Text>
          <View style={s.rowBetween}><Btn title="Previous week" onPress={() => shift(-7)} /><Text style={s.small}>{data.week_start} to {data.week_end}</Text><Btn title="Next week" onPress={() => shift(7)} /></View>
          <Text style={[s.title, { marginVertical: 8 }]}>{data.total} of {data.target} hours</Text>
          <Err msg={msg} />
        </>}
        ListEmptyComponent={<Text style={s.sub}>No time logged this week.</Text>}
        renderItem={({ item: e }) => (
          <View style={s.card}>
            <View style={s.rowBetween}><Text style={s.title}>{e.work_date} · {e.hours} h</Text><Pill text={e.status} /></View>
            <Text style={s.small}>{e.project}{e.task ? ` · ${e.task}` : ''}</Text>
            {!!e.reject_reason && <Text style={[s.small, { color: C.bad }]}>Rejected: {e.reject_reason}</Text>}
            {e.editable && <View style={s.wrap}><Btn title="Delete" kind="danger" onPress={() => del(e)} /></View>}
          </View>)} />
      <View style={s.bar}><Btn title="Add time" onPress={() => setAdding(true)} /><Btn title="Submit week" kind="pri" disabled={!data.submittable} onPress={submit} /></View>
      <AddTime visible={adding} week={data} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); reload() }} />
    </View>
  )
}

function AddTime({ visible, week, onClose, onSaved }: { visible: boolean; week: Week; onClose: () => void; onSaved: () => void }) {
  const projs = useLoad<Proj[]>('/api/timesheets/projects')
  const [project, setProject] = useState(0)
  const [task, setTask] = useState(0)
  const [date, setDate] = useState('')
  const [hours, setHours] = useState('')
  const [err, setErr] = useState('')
  const today = iso(new Date())
  const day = date || (today >= week.week_start && today <= week.week_end ? today : week.week_start)
  async function save() {
    setErr('')
    try { await api('/api/timesheets', { method: 'POST', body: { project_id: project, task_id: task || null, work_date: day, hours: parseFloat(hours), note: '' } }); setHours(''); onSaved() } catch (e) { setErr((e as Error).message) }
  }
  const tasks = projs.data?.find((p) => p.id === project)?.tasks ?? []
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={{ flex: 1, backgroundColor: C.bg }}><ScrollView contentContainerStyle={{ padding: 18 }}>
        <Text style={s.h1}>Add time</Text>
        <Text style={s.label}>Project</Text>
        <View style={s.wrap}>{projs.data?.map((p) => <Pressable key={p.id} onPress={() => { setProject(p.id); setTask(0) }} style={[s.chip, project === p.id && s.chipOn]}><Text style={project === p.id ? { color: '#fff' } : { color: C.ink }}>{p.label}</Text></Pressable>)}</View>
        {tasks.length > 0 && <><Text style={s.label}>Task (optional)</Text><View style={s.wrap}>{tasks.map((t) => <Pressable key={t.id} onPress={() => setTask(task === t.id ? 0 : t.id)} style={[s.chip, task === t.id && s.chipOn]}><Text style={task === t.id ? { color: '#fff' } : { color: C.ink }}>{t.title}</Text></Pressable>)}</View></>}
        <Text style={s.label}>Date (YYYY-MM-DD)</Text>
        <TextInput style={s.input} value={date || day} onChangeText={setDate} accessibilityLabel="Date" />
        <Text style={s.label}>Hours</Text>
        <TextInput style={s.input} value={hours} onChangeText={setHours} keyboardType="decimal-pad" accessibilityLabel="Hours" />
        <Err msg={err} />
        <View style={s.wrap}><Btn title="Cancel" onPress={onClose} /><Btn title="Save time" kind="pri" disabled={!project || !hours} onPress={save} /></View>
      </ScrollView></SafeAreaView>
    </Modal>
  )
}

// ---------------- handover ----------------
function Handovers() {
  const { data, error, loading, reload } = useLoad<Handover[]>('/api/handovers')
  const [err, setErr] = useState('')
  async function ack(h: Handover) { setErr(''); try { await api(`/api/handovers/${h.id}/ack`, { method: 'POST', body: { note: '' } }); reload() } catch (e) { setErr((e as Error).message) } }
  if (loading && !data) return <Wait />
  return (
    <FlatList data={data ?? []} keyExtractor={(h) => String(h.id)} onRefresh={reload} refreshing={loading} contentContainerStyle={{ padding: 14 }}
      ListHeaderComponent={<><Text style={s.h1}>Handovers</Text><Err msg={error || err} /></>}
      ListEmptyComponent={<Text style={s.sub}>No handovers for you.</Text>}
      renderItem={({ item: h }) => (
        <View style={s.card}>
          <View style={s.rowBetween}><Text style={s.title}>{h.from} to {h.to}</Text><Pill text={h.status} /></View>
          <Text style={s.small}>{h.project}</Text>
          <Text style={{ marginVertical: 6, color: C.ink }}>{h.note}</Text>
          {h.tasks.map((t) => <Text key={t.id} style={s.small}>• {t.title}</Text>)}
          {h.can_ack && <View style={s.wrap}><Btn title="Acknowledge handover" kind="pri" onPress={() => ack(h)} /></View>}
        </View>)} />
  )
}

// ---------------- notifications ----------------
function Notices() {
  const { data, error, loading, reload } = useLoad<Notice>('/api/notifications')
  useEffect(() => { if (data?.unread) api('/api/notifications/read', { method: 'POST' }).catch(() => {}) }, [data])
  if (loading && !data) return <Wait />
  return (
    <FlatList data={data?.items ?? []} keyExtractor={(n) => String(n.id)} onRefresh={reload} refreshing={loading} contentContainerStyle={{ padding: 14 }}
      ListHeaderComponent={<><Text style={s.h1}>Notifications</Text><Err msg={error} /></>}
      ListEmptyComponent={<Text style={s.sub}>Nothing new.</Text>}
      renderItem={({ item: n }) => <View style={s.card}><Text style={{ color: C.ink, fontWeight: n.read ? '400' : '700' }}>{n.text}</Text><Text style={s.small}>{n.at.slice(0, 16).replace('T', ' ')}</Text></View>} />
  )
}

// ---------------- shell ----------------
const TABS = ['Tasks', 'Timesheet', 'Handover', 'Alerts'] as const
export default function App() {
  const [me, setMe] = useState<Me | null>(null)
  const [tab, setTab] = useState<(typeof TABS)[number]>('Tasks')
  const load = useCallback(async () => { try { setMe(await api<Me>('/api/me')) } catch (e) { Alert.alert('Could not load your profile', (e as ApiError).message) } }, [])
  if (!me) return <SafeAreaView style={s.root}><StatusBar style="dark" /><Login onDone={load} /></SafeAreaView>
  return (
    <SafeAreaView style={s.root}>
      <StatusBar style="dark" />
      <View style={s.top}><View style={{ flex: 1 }}><Text style={s.title}>{me.user.name}</Text><Text style={s.small}>{me.role.name} · {me.tenant.name}</Text></View><Btn title="Sign out" onPress={() => { signOut(); setMe(null) }} /></View>
      {me.tenant.demo && <Text style={s.banner}>Illustrative demo data, not real records</Text>}
      <View style={{ flex: 1 }}>{tab === 'Tasks' ? <Tasks /> : tab === 'Timesheet' ? <Timesheet /> : tab === 'Handover' ? <Handovers /> : <Notices />}</View>
      <View style={s.tabs} accessibilityRole="tablist">{TABS.map((t) => (
        <Pressable key={t} accessibilityRole="tab" accessibilityState={{ selected: tab === t }} onPress={() => setTab(t)} style={s.tab}><Text style={[s.tabT, tab === t && { color: C.acc, fontWeight: '700' }]}>{t}</Text></Pressable>))}</View>
    </SafeAreaView>
  )
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  h1: { fontSize: 22, fontWeight: '700', color: C.ink, marginBottom: 6 }, h2: { fontSize: 17, fontWeight: '700', color: C.ink },
  sub: { color: C.mute, marginBottom: 10 }, small: { color: C.mute, fontSize: 12.5 }, title: { color: C.ink, fontWeight: '600', fontSize: 15, flexShrink: 1 },
  label: { fontWeight: '600', color: C.ink, marginTop: 10, marginBottom: 4 },
  input: { backgroundColor: '#fff', borderWidth: 1, borderColor: C.line, borderRadius: 8, padding: 10, fontSize: 15 },
  card: { backgroundColor: '#fff', borderWidth: 1, borderColor: C.line, borderRadius: 10, padding: 12, marginTop: 10 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginVertical: 4 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  btn: { borderWidth: 1, borderColor: C.line, borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12, backgroundColor: '#fff', minHeight: 40, justifyContent: 'center' },
  btnT: { color: C.ink, fontWeight: '600' },
  pill: { borderWidth: 1, borderRadius: 99, paddingHorizontal: 8, paddingVertical: 1, fontSize: 12, fontWeight: '600' },
  chip: { borderWidth: 1, borderColor: C.line, borderRadius: 99, paddingVertical: 8, paddingHorizontal: 12, backgroundColor: '#fff' }, chipOn: { backgroundColor: C.acc, borderColor: C.acc },
  err: { color: C.bad, marginVertical: 6 },
  top: { flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 1, borderColor: C.line, backgroundColor: '#fff', gap: 8 },
  banner: { backgroundColor: '#fff4d6', color: C.warn, padding: 6, textAlign: 'center', fontSize: 12 },
  bar: { flexDirection: 'row', justifyContent: 'space-between', padding: 12, borderTopWidth: 1, borderColor: C.line, backgroundColor: '#fff' },
  tabs: { flexDirection: 'row', borderTopWidth: 1, borderColor: C.line, backgroundColor: '#fff' }, tab: { flex: 1, padding: 14, alignItems: 'center' }, tabT: { color: C.mute },
})
