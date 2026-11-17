import type {ComponentType} from 'react';
import type {GameState} from './GameResult';
export interface GameRuntime {sync(remainingMs:number,now?:number):void;remaining(now?:number):number;allowInput(now?:number):boolean}
export type GameBoardProps={state:GameState;remaining:number;disabled:boolean;onInput:(cell:number)=>void};
export interface GameModule {id:string;create:()=>GameRuntime;Board:ComponentType<GameBoardProps>}
