// The oldhand theme. `astryx experimental theme editor` wrote this file once and never changes it again.
// The checked settings live in oldhand.settings.json and the generated oldhand.settings.ts;
// change them with `astryx experimental theme editor set oldhand ...`. Add your own changes below: they win over the settings.
import {defineTheme} from '@astryxdesign/core/theme';
import {oldhandSettings} from './oldhand.settings';

export const oldhandTheme = defineTheme({
  extends: oldhandSettings,
  name: 'oldhand',
});
