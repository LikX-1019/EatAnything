import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getHomeAnnouncements, getUnreadCount, type MessageItem } from '@/api/messages'

export const useMessageStore=defineStore('messages',()=>{
  const unreadCount=ref(0);const announcements=ref<MessageItem[]>([]);let timer:ReturnType<typeof setInterval>|null=null
  async function refreshUnread(){const data=await getUnreadCount();unreadCount.value=data.count}
  async function refreshAnnouncements(){announcements.value=await getHomeAnnouncements()}
  function consumeRead(){if(unreadCount.value>0)unreadCount.value-=1}
  function clearUnread(){unreadCount.value=0}
  function startPolling(){stopPolling();void refreshUnread().catch(()=>undefined);timer=setInterval(()=>void refreshUnread().catch(()=>undefined),60000)}
  function stopPolling(){if(timer)clearInterval(timer);timer=null}
  return{unreadCount,announcements,refreshUnread,refreshAnnouncements,consumeRead,clearUnread,startPolling,stopPolling}
})
