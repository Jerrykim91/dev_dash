import type {GameDefinition} from './GameResult';
import type {GameModule} from './GameModule';
import {WhackAMoleGame} from '../whack-a-mole/WhackAMoleGame';
import {WhackAMoleBoard} from '../whack-a-mole/WhackAMoleBoard';
export const GameRegistry=new Map<string,GameModule>([['whack_a_mole',{id:'whack_a_mole',create:()=>new WhackAMoleGame(),Board:WhackAMoleBoard}]]);
export const canPlay=(game:GameDefinition)=>game.available&&GameRegistry.has(game.game_id);
