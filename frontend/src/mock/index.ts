import { createProdMockServer } from "vite-plugin-mock/es/createProdMockServer";

import userModule from "./user/index";
import systemModule from "./system/index";
import fileModule from "./file/index";
import monitorModule from "./monitor/index";

export function setupProdMockServer() {
  createProdMockServer([...userModule, ...systemModule, ...fileModule, ...monitorModule]);
}
