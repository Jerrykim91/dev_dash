import maps from '../../../shared/maps.json';
import rooms from '../../../shared/rooms.json';
import personal from '../../../shared/personal-room.json';
import type {MapData} from './types';
export const officeWorld=maps.office as MapData;
export const roomWorlds=rooms.maps as Record<string,MapData>;
export const roomDefinitions=rooms.definitions;
export const mapFor=(_zone?:string):MapData=>officeWorld;

export const personalRoom=personal as MapData;
export const mapForScope=(scope:string):MapData=>scope.startsWith('personal:')?personalRoom:officeWorld;
