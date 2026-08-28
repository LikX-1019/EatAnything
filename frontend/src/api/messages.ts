import { get, patch, post } from './client'

export type MessageKind='notification'|'announcement'
export interface MessageItem{id:string;kind:MessageKind;source:string;eventType?:string|null;title:string;bodyHtml:string;priority:'normal'|'important';actionType?:string|null;actionTargetId?:string|null;publishAt:string;expireAt?:string|null;isRead:boolean}
export interface MessagePage{items:MessageItem[];page:number;pageSize:number;total:number}
export interface NotificationSettings{available:boolean;wechatEnabled:boolean;templates:Record<MessageKind,{templateId?:string|null;status:string}>}

export interface MessageQuery { kind?: MessageKind; unreadOnly?: boolean; page?: number; pageSize?: number }
interface MessageQueryPayload { kind?: MessageKind; unread_only?: boolean; page: number; page_size: number }

export function getMessages(params: MessageQuery = {}) {
  const query: MessageQueryPayload = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
  }
  if (params.kind) query.kind = params.kind
  if (params.unreadOnly !== undefined) query.unread_only = params.unreadOnly
  return get<MessagePage, MessageQueryPayload>('/me/messages', query)
}
export function getUnreadCount(){return get<{count:number}>('/me/messages/unread-count')}
export function getMessage(id:string){return get<MessageItem>(`/me/messages/${encodeURIComponent(id)}`)}
export function markMessageRead(id:string){return post(`/me/messages/${encodeURIComponent(id)}/read`)}
export function markAllMessagesRead(kind?:MessageKind){return post<{affectedCount:number}>(`/me/messages/read-all${kind?`?kind=${kind}`:''}`)}
export function getHomeAnnouncements(){return get<MessageItem[]>('/me/announcements/home')}
export function getNotificationSettings(){return get<NotificationSettings>('/me/notification-settings')}
export function updateNotificationSettings(wechatEnabled:boolean){return patch<{wechatEnabled:boolean}, {wechatEnabled:boolean}>('/me/notification-settings',{wechatEnabled})}
export function saveWechatConsent(data:{notification?:'accept'|'reject'|'ban';announcement?:'accept'|'reject'|'ban'}){return post<NotificationSettings,typeof data>('/me/notification-settings/wechat-consent',data)}
