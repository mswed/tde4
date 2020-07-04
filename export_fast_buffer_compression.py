# 3DE4.script.name: Export Fast Buffer Compression File...
# 3DE4.script.version: v1.6
# 3DE4.script.gui: Main Window::Playback
# 3DE4.script.comment: Generates Buffer Compression Files for Sequence Cameras
# 3DE4.script.comment: using hyperthreading.

# v1.0 2014/07/03 by Helder Thomas.
# v1.1 2014/08/01 by Rolf Schneider (rolf@sci-d-vis.com).
# v1.2 2014/12/10 by Helder Thomas:
#      Updated to support multiple cameras/selections.
# v1.2 2015/04/03 by S.W.
# v1.3 2015/04/09 by Rolf Schneider (rolf@sci-d-vis.com):
#      Code merged both v1.2s.
# v1.4 2018/10/13 by Unai Martinez Barredo (unaimb.com),
#                 for Jellyfish Pictures Ltd (jellyfishpictures.co.uk):
#      Fixed Windows functionality and overall revamp.
# v1.5 2018/10/16 by RS
#                 code merge with Unai's v1.4, added support for sxr & exr options of "makeBCFile"
# v1.6 2020/07/03 by Moshe Swed: pulls buffer location from preferences

# Required 3DE Version: Unknown.

import os
import subprocess

import tde4

TITLE = 'Export Fast Buffer Compression File...'


def compress(cams, ui=False):
    errors = []
    max_steps = 0
    seq_cams = {}

    for cam in cams:
        cam_name = tde4.getCameraName(cam)

        if tde4.getCameraType(cam) != 'SEQUENCE':
            errors.append(
                'Camera {} is not a Sequence Camera.'.format(cam_name))
            continue

        start, end = tde4.getCameraSequenceAttr(cam)[:2]
        frames = abs(end - start + 1)
        steps = frames + frames / 100 + 2
        max_steps += steps
        seq_cams[cam] = {'name': cam_name, 'start': start, 'end': end,
                         'frames': frames, 'steps': steps}

    if cams:
        if ui:
            tde4.postProgressRequesterAndContinue(TITLE, 'Please wait...',
                                                  max_steps, 'Ok')
        else:
            print(TITLE)
    else:
        errors.append('Please choose a camera.')

    steps_done = 0

    for cam in seq_cams:
        cam_name = seq_cams[cam]['name']
        msg = 'Exporting: {} (starting)'.format(cam_name)
        if ui:
            tde4.updateProgressRequester(steps_done, msg)
        else:
            print('  0% ' + msg)
        start = seq_cams[cam]['start']
        end = seq_cams[cam]['end']
        frames = seq_cams[cam]['frames']
        steps = seq_cams[cam]['steps']
        path = tde4.getCameraPath(cam)

        if tde4.getPreferenceValue('ICOMPRESS_BCFILE_IN_DIR') == '1':
            # save buffer in project directory
            project_dir = os.path.dirname(tde4.getProjectPath())
            if project_dir:
                # we have a project directory, it's safe to save
                target_path = os.path.join(project_dir, os.path.basename(path))
            else:
                # no project directory, alert the user
                target_path = ''
                errors.append('Can not save buffer to project directory. Project is not saved.')
        elif tde4.getPreferenceValue('ICOMPRESS_BCFILE_IN_DIR') == '2':
            # save buffer in custom directory
            custom_dir = tde4.getPreferenceValue('ICOMPRESS_CUSTOM_DIR')
            target_path = os.path.join(custom_dir, os.path.basename(path))
        else:
            # default behavior, save buffer in image path
            target_path = path

        if not path:
            errors.append(("Couldn't process camera {} because it doesn't have "
                           'any Footage loaded.').format(cam_name))
            steps_done += steps
            continue

        gamma = tde4.getCamera8BitColorGamma(cam)
        softclip = tde4.getCamera8BitColorSoftclip(cam)
        black, white = tde4.getCamera8BitColorBlackWhite(cam)
        exr = tde4.getCameraImportEXRDisplayWindowFlag(cam)
        sxr = tde4.getCameraImportSXRRightEyeFlag(cam)
        if sxr == 1:
            sxr2 = " -import_sxr_right_eye "
        else:
            sxr2 = " "
        if exr == 1:
            exr2 = " -import_exr_display_window "
        else:
            exr2 = " "
        proc_err = None

        # makeBCFile exits cleanly even if it errored, so we have to parse
        # its errors manually.
        proc = subprocess.Popen((os.path.join(tde4.get3DEInstallPath(), 'bin', 'makeBCFile'), '-source', path, '-start',
                                 str(start), '-end', str(end), '-out', os.path.dirname(target_path), sxr2, exr2,
                                 '-black', str(black), '-white', str(white), '-gamma', str(gamma), '-softclip',
                                 str(softclip)),
                                stdout=subprocess.PIPE, universal_newlines=True)

        for line in iter(proc.stdout.readline, ''):
            line = line.rstrip()

            if line.startswith('Error'):
                proc_err = line
                continue
            elif line.endswith('image files processed'):
                frame = int(line.split('/', 1)[0])
                msg = 'Exporting: {} ({}/{})'.format(cam_name, frame, frames)
                if ui:
                    tde4.updateProgressRequester(steps_done + frame + 1, msg)
                else:
                    print('{: 3d}% {}'.format(100 * (steps_done + frame + 1) / max_steps, msg))

        if proc_err:
            errors.append("Couldn't create Buffer Compression File for Camera {}.".format(cam_name))
            errors.append('Message >>    {}'.format(proc_err))
            steps_done += steps
            continue

        msg = 'Exporting: {} (finishing)'.format(cam_name)
        if ui:
            tde4.updateProgressRequester(steps_done + frames + 2, msg)
        else:
            print('{: 3d}% {}'.format(100 * (steps_done + frames + 2) / max_steps, msg))
        bcompress = ('x'.join(target_path.split('#' * path.count('#'))) + '.3de_bcompress')

        if not os.path.isfile(bcompress):
            errors.append("Couldn't find Buffer Compression File for Camera {}.".format(cam_name))
            steps_done += steps
            continue

        if not tde4.importBufferCompressionFile(cam):
            errors.append("Couldn't import Buffer Compression File for Camera {}.".format(cam_name))

        # Change permissions of the Buffer Compression File,
        # to be nice to everyone else who might work on the shot eventually!
        try:
            os.chmod(bcompress, 0o666)
        except OSError:
            errors.append("Couldn't set permissions of Buffer CompressionFile for Camera {}.".format(cam_name))

        steps_done += steps

    if ui:
        tde4.unpostProgressRequester()

        if errors:
            req = tde4.createCustomRequester()
            for i, line in enumerate(errors):
                name = 'line{}'.format(i)
                tde4.addLabelWidget(req, name, line, 'ALIGN_LABEL_LEFT')
                tde4.setWidgetOffsets(req, name, 0, 0, 0, 0)
            tde4.postCustomRequester(req, TITLE, 0, 0, 'Ok')

    else:
        print('100% Done.')

        if errors:
            raise RuntimeError('\n'.join(errors))


if __name__ == '__main__':
    req = tde4.createCustomRequester()
    tde4.addOptionMenuWidget(req, 'mode', 'Export:', 'Current Camera',
                             'Selected Cameras', 'All Cameras')
    ret = tde4.postCustomRequester(req, TITLE, 300, 0, 'Export', 'Cancel')

    if ret == 1:
        mode = tde4.getWidgetValue(req, 'mode')

        if mode == 1:
            cams = [tde4.getCurrentCamera()]
        else:
            cams = tde4.getCameraList(mode < 3)

        compress(cams, ui=True)

    tde4.deleteCustomRequester(req)
