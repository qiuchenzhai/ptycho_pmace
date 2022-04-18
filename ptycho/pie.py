from utils.utils import *
from utils.nrmse import *
from utils.display import *
import random


def epie_recon(init_obj_guess, diffraction_data, projection_coords, obj_ref, probe_ref,
               num_iter=100, step_sz=1, display_win=None, display=False, save_dir=None):
    """
    ePIE reconstruction to perform single estimate on complex transmittance of complex
    object assuming known complex probe function.
    :param init_obj_guess: formulated initial guess of complex transmittance of complex object image.
    :param diffraction_data: pre-processed diffraction patterns (phase-less measurements).
    :param projection_coords: scan coordinates of projections.
    :param obj_ref: ground truth image or reference image.
    :param probe_ref: known or estimated complex probe function.
    :param num_iter: number of iterations.
    :param step_sz: step size parameter for object update function.
    :param display_win: pre-defined cover/window for comparing reconstruction results.
    :param display: option to display the reconstruction results.
    :param save_dir: save reconstruction results to the given directory.
    :return: reconstructed complex transmittance of complex object and error metrics.
    """

    # check directories for saving files
    if save_dir is not None:
        obj_fname = save_dir + 'ePIE_img_revy'
        os.makedirs(save_dir, exist_ok=True)

    if display_win is None:
        display_win = np.ones(init_obj_guess.shape)

    # initialization
    num_agts, m, n = diffraction_data.shape
    obj_est = np.copy(init_obj_guess).astype(np.complex128)
    probe = np.copy(probe_ref)
    seq = np.arange(0, num_agts, 1).tolist()
    obj_nrmse_ls = []
    diffr_nrmse_ls = []
    time_ls = []
    start_time = time.time()

    # ePIE reconstruction
    print('ePIE starts ...')
    for i in range(num_iter):
        projected_patch = img2patch(obj_est, projection_coords, diffraction_data.shape)
        frm = np.copy(projected_patch) * probe
        frm_update = np.zeros(frm.shape, dtype=np.complex128)
        random.shuffle(seq)
        for j in seq:
            # FT{D*P_j*v}]
            freq = compute_ft(frm[j])
            # y \times FT{D*P_j*v} / |FT{D*P_j*v}|
            freq_update = diffraction_data[j] * np.exp(1j * np.angle(freq))
            # IFT{y \times FT{D*P_j*v} / |FT{D*P_j*v}|}
            frm_update[j] = compute_ift(freq_update)
            # ePIE update
            obj_est[projection_coords[j, 0]:projection_coords[j, 1], projection_coords[j, 2]:projection_coords[j, 3]] += \
                step_sz * np.conj(probe) * (frm_update[j] - frm[j]) / np.max(np.abs(probe)) ** 2

        # calculate time consumption
        elapsed_time = time.time() - start_time
        time_ls.append(elapsed_time)

        # compute the nrmse error between propagted reconstruction result and recorded measurements
        diffraction_est = np.abs(compute_ft(probe * img2patch(np.copy(obj_est), projection_coords, diffraction_data.shape)))
        diffr_nrmse_val = compute_nrmse(diffraction_est, diffraction_data, np.ones(diffraction_data.shape))
        diffr_nrmse_ls.append(diffr_nrmse_val)

        # phase normalization and compute the nrmse error between reconstructed image and reference image
        obj_revy = phase_norm(np.copy(obj_est) * display_win, np.copy(obj_ref) * display_win)
        obj_nrmse_val = compute_nrmse(obj_revy * display_win, obj_ref * display_win, display_win)
        obj_nrmse_ls.append(obj_nrmse_val)
        print('iter =', i, 'img_error =', obj_nrmse_val, 'diffr_err =', diffr_nrmse_val)

    # save recon results
    save_tiff(obj_est, save_dir + 'obj_est_iter_{}.tiff'.format(i + 1))
    save_array(obj_nrmse_ls, save_dir + 'obj_nrmse')
    save_array(diffr_nrmse_ls, save_dir + 'diffr_nrmse')

    # display the reconstructed image and convergence plot
    plot_cmplx_obj(obj_revy, obj_ref, img_title='ePIE', display_win=display_win, display=display, save_fname=obj_fname)
    xlabel, ylabel, line_label = 'Number of iterations', 'object NRMSE', r'ePIE ($step size$ = {})'.format(step_sz)
    plot_nrmse(obj_nrmse_ls, title='Convergence plot of ePIE algorithm', label=[xlabel, ylabel, line_label],
               step_sz=15, fig_sz=[8, 4.8], display=display, save_fname=save_dir + 'convergence_obj_nrmse')
    xlabel, ylabel, line_label = 'Number of iterations', 'diffraction NRMSE', r'ePIE ($step size$ = {})'.format(step_sz)
    plot_nrmse(diffr_nrmse_ls, title='Convergence plot of ePIE algorithm', label=[xlabel, ylabel, line_label],
               step_sz=15, fig_sz=[8, 4.8], display=display, save_fname=save_dir + 'convergence_diffr_nrmse')

    # return the result
    keys = ['obj_revy', 'obj_err', 'diffr_err']
    vals = [obj_revy, obj_nrmse_ls, diffr_nrmse_ls]
    output = dict(zip(keys, vals))

    return output


def epie_joint_recon(init_obj, init_probe, diffraction_data, projection_coords, obj_ref=None, probe_ref=None,
                     num_iter=100, obj_step_sz=1, probe_step_sz=1, display_win=None, display=False, save_dir=None):
    """
    Function to perform PIE-type approach for ptychographic image reconstruction.
    :param init_obj: initialized complex object.
    :param init_probe: initialized complex probe.
    :param diffraction_data: pre-processed phaseless measurements (diffraction patterns).
    :param projection_coords: coordinates of projections.
    :param obj_ref: ground truth image.
    :param probe_ref: ground truth probe.
    :param num_iter: number of iteration.
    :param obj_step_sz: step size of object update function.
    :param probe_step_sz: step size of probe update function.
    :param display_win: reconstruction window.
    :param display: display the reconstruction results.
    :param save_dir: path for saving reconstructed images.
    :return: reconstructed complex image and probe and nrmse.
    """

    # check directories for saving files
    if save_dir is None:
        obj_fname = None
        probe_fname = None
    else:
        obj_fname = save_dir + 'ePIE_img_revy'
        probe_fname = save_dir + 'ePIE_probe_revy'
        os.makedirs(save_dir, exist_ok=True)

    if display_win is None:
        display_win = np.ones(init_obj.shape)

    # initialization
    obj_nrmse_ls = []
    probe_nrmse_ls = []
    diffr_nrmse_ls = []
    seq = np.arange(0, len(diffraction_data), 1).tolist()
    obj_est = np.asarray(np.copy(init_obj), dtype=np.complex128)
    probe_est = np.asarray(np.copy(init_probe), dtype=np.complex128)

    # ePIE reconstruction
    print('ePIE joint recon starts ...')
    start_time = time.time()
    for i in range(num_iter):
        random.shuffle(seq)
        # update the complex object and probe estimates sequentially
        for j in seq:
            # for j in range(num_agts):
            crds0, crds1, crds2, crds3 = projection_coords[j, 0], projection_coords[j, 1], projection_coords[j, 2], projection_coords[j, 3]
            projected_img = np.copy(obj_est[crds0:crds1, crds2:crds3])
            frm = projected_img * np.copy(probe_est)
            # FT
            freq = compute_ft(frm)
            freq_update = diffraction_data[j] * divide_cmplx_numbers(np.copy(freq), np.abs(np.copy(freq)))
            # freq_update = diffr[j] * np.copy(freq) / np.abs(np.copy(freq))
            # update image and probe est
            delta_frm = compute_ift(freq_update) - frm
            obj_est[crds0:crds1, crds2:crds3] += obj_step_sz * np.conj(probe_est) * delta_frm / (np.amax(np.abs(probe_est)) ** 2)
            probe_est += probe_step_sz * np.conj(projected_img) * delta_frm / (np.amax(np.abs(projected_img)) ** 2)

        # compute the nrmse error between propagted reconstruction result and recorded measurements
        diffraction_est = np.abs(compute_ft(probe_est * img2patch(np.copy(obj_est), projection_coords, diffraction_data.shape)))
        diffr_nrmse_val = compute_nrmse(diffraction_est, diffraction_data)
        diffr_nrmse_ls.append(diffr_nrmse_val)

        # phase normalization and scale image to minimize the intensity difference
        if obj_ref is not None:
            obj_revy = phase_norm(np.copy(obj_est) * display_win, obj_ref * display_win)
        else:
            obj_revy = obj_est
            obj_ref = obj_revy
        if probe_ref is not None:
            probe_revy = phase_norm(np.copy(probe_est), probe_ref)
        else:
            probe_revy = probe_est
            probe_ref = probe_revy

        # compute the nrmse error
        img_nrmse_val = compute_nrmse(obj_revy * display_win, obj_ref * display_win, display_win)
        obj_nrmse_ls.append(img_nrmse_val)
        probe_nrmse_val = compute_nrmse(probe_revy, probe_ref, np.ones(probe_revy.shape))
        probe_nrmse_ls.append(probe_nrmse_val)
        print('iter =', i, 'img_nrmse =', img_nrmse_val, 'probe_nrmse =', probe_nrmse_val, 'diffr_err =', diffr_nrmse_val)

    # calculate time consumption
    elapsed_time = time.time() - start_time
    print('Time consumption of ePIE:', elapsed_time)

    # save recon results
    save_tiff(obj_est, save_dir + 'obj_est_iter_{}.tiff'.format(i + 1))
    save_tiff(probe_est, save_dir + 'probe_est_iter_{}.tiff'.format(i + 1))
    save_array(obj_nrmse_ls,  save_dir + 'obj_nrmse')
    save_array(probe_nrmse_ls, save_dir + 'probe_nrmse')
    save_array(diffr_nrmse_ls, save_dir + 'diffr_nrmse')

    # display the reconstructed image and probe
    plot_cmplx_obj(obj_revy, obj_ref, img_title='ePIE', display_win=display_win, display=display, save_fname=obj_fname)
    plot_cmplx_probe(probe_revy, probe_ref, img_title='ePIE', display=display, save_fname=probe_fname)

    # return the result
    keys = ['obj_revy', 'probe_revy', 'obj_err', 'probe_err', 'diffr_err']
    vals = [obj_revy, probe_revy, obj_nrmse_ls, probe_nrmse_ls, diffr_nrmse_ls]
    output = dict(zip(keys, vals))

    return output

