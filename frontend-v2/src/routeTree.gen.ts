/**
 * Hand-written route tree (in lieu of `@tanstack/router-plugin`'s
 * generator output). Mirrors `src/routes/*.tsx` 1:1.
 *
 * If you adopt the plugin later, delete this file and add
 * `@tanstack/router-plugin/vite` to vite.config.ts.
 */

import { Route as RootRoute } from "./routes/__root";
import { Route as IndexRoute } from "./routes/index";
import { Route as VillainsListRoute } from "./routes/villains.index";
import { Route as VillainProfileRoute } from "./routes/villains.$name";
import { Route as HandDetailRoute } from "./routes/hands.$id";
import { Route as SearchByDecisionRoute } from "./routes/search.by-decision";
import { Route as SearchByActionPathRoute } from "./routes/search.by-action-path";
import { Route as SearchBySpotBuilderRoute } from "./routes/search.by-spot-builder";
import { Route as UploadRoute } from "./routes/upload";

export const routeTree = RootRoute.addChildren([
  IndexRoute,
  VillainsListRoute,
  VillainProfileRoute,
  HandDetailRoute,
  SearchByDecisionRoute,
  SearchByActionPathRoute,
  SearchBySpotBuilderRoute,
  UploadRoute,
]);
