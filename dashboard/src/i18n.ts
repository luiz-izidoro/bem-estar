export type Language = 'pt-BR' | 'en'

const pt = {
  overview: 'Hoje', training: 'Treino', data: 'Dados', settings: 'Configurações',
  signIn: 'Entrar', username: 'Usuário', password: 'Senha', welcome: 'Seu panorama de hoje',
  readiness: 'Prontidão', recovery: 'Recuperação', sleep: 'Sono', hrv: 'HRV', restingHr: 'FC repouso',
  trainingLoad: 'Carga de treino', fitness: 'CTL · Fitness', fatigue: 'ATL · Fadiga', balance: 'TSB · Balanço', acwr: 'ACWR',
  recentWorkouts: 'Treinos recentes', ingestion: 'Sincronização HAE', insight: 'Insight do dia', refresh: 'Atualizar',
  noData: 'Sem dados ainda', processed: 'processado', pending: 'pendente', failed: 'falhou', language: 'Idioma', grafana: 'Abrir Grafana',
  profileHint: 'TRIMP usa sua FC máxima e de repouso. Ajuste abaixo antes de interpretar carga de treino.',
  maxHr: 'FC máxima', restingHrSetting: 'FC de repouso', targetSleep: 'Meta de sono (h)', trimpCoefficient: 'Coeficiente TRIMP', saveProfile: 'Salvar perfil e recalcular', saved: 'Perfil salvo',
  privacy: 'Dados privados · métricas determinísticas e versionadas'
}
const en = {
  overview: 'Today', training: 'Training', data: 'Data', settings: 'Settings',
  signIn: 'Sign in', username: 'Username', password: 'Password', welcome: 'Your overview for today',
  readiness: 'Readiness', recovery: 'Recovery', sleep: 'Sleep', hrv: 'HRV', restingHr: 'Resting HR',
  trainingLoad: 'Training load', fitness: 'CTL · Fitness', fatigue: 'ATL · Fatigue', balance: 'TSB · Balance', acwr: 'ACWR',
  recentWorkouts: 'Recent workouts', ingestion: 'HAE sync', insight: 'Daily insight', refresh: 'Refresh',
  noData: 'No data yet', processed: 'processed', pending: 'pending', failed: 'failed', language: 'Language', grafana: 'Open Grafana',
  profileHint: 'TRIMP uses your max and resting HR. Set them below before interpreting training load.',
  maxHr: 'Max HR', restingHrSetting: 'Resting HR', targetSleep: 'Sleep target (h)', trimpCoefficient: 'TRIMP coefficient', saveProfile: 'Save profile and recompute', saved: 'Profile saved',
  privacy: 'Private data · deterministic, versioned metrics'
}
export const strings = { 'pt-BR': pt, en }
