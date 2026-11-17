import type {GameState} from './GameResult';
export class GameSession {
 state:GameState|null=null;
 accept(next:GameState){if(this.state?.session_id===next.session_id&&(next.server_now<this.state.server_now||(this.state.status!=='active'&&next.status==='active')))return this.state;this.state=next;return next;}
 constructor(private token:string){}
 start(game_id:string,request_id:string){return this.request<GameState>('/games/sessions',{game_id,request_id});}
 progress(id:string){return this.request<GameState>(`/games/sessions/${id}`);}
 finish(id:string,cancel=false){return this.request<GameState>(`/games/sessions/${id}/${cancel?'cancel':'finish'}`,{});}
 async request<T>(path:string,body?:unknown):Promise<T>{const response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:{Authorization:`Bearer ${this.token}`,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});let data;try{data=await response.json();}catch{throw Error('서버 응답을 확인하지 못했어요. 잠시 후 다시 시도해 주세요.');}if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'올바른 게임 요청인지 확인해 주세요.');return data;}
}
