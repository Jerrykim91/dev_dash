import type {UserAvatarContext} from '../game/types';
export const DASHBOARD_KEY='nobis.dashboard-url';
export function readDashboardUrl():string {return import.meta.env.VITE_DEVNEST_URL||'';}
export function validateDashboardUrl(value:string,production=false):boolean {
 if(!value.trim())return true;
 try {const u=new URL(value),host=u.hostname.toLowerCase().replace(/\.$/,'');return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password&&(!production||!(host==='localhost'||host.endsWith('.localhost')||/^127\./.test(host)||host==='0.0.0.0'||host==='[::1]'||host==='[0:0:0:0:0:0:0:1]'));}catch{return false;}
}
export function dashboardLink(url:string,returnTo:string,_context:UserAvatarContext):string {
 // Context is a shared future contract. Never pass tokens or claim shared authentication.
 const target=new URL(url);target.searchParams.set('return_to',returnTo);return target.toString();
}
