export class WhackAMoleGame {
 private deadline=0;private lastInput=-Infinity;
 sync(remainingMs:number,now=performance.now()){this.deadline=now+remainingMs;}
 remaining(now=performance.now()){return Math.max(0,this.deadline-now);}
 allowInput(now=performance.now()){if(now-this.lastInput<100)return false;this.lastInput=now;return true;}
}
