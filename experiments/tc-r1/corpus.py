"""Author/verify TC-R1 primary assets without executing PBRT or any policy."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path('research/tc-r1/corpus')
PBRT_COMMIT = 'b4ce9687e6c695f5582997c61b0c66cf064bdb4a'
FAMILIES = dict(uniform='uniformly-noisy', specular='highly-specular',
                diffuse='simple-diffuse', motion='motion-heavy',
                adaptive='adaptive-sampling-friendly')
TIMES = [0, 0.5, 1]
ENVELOPE = dict(backend='cpu-float', integrator='path', maxdepth=8, regularize=False,
                film='rgb', filter='box', camera='perspective-pinhole', sampler='independent',
                geometry=['sphere', 'trianglemesh'], materials=['diffuse', 'conductor', 'dielectric'],
                lights=['point', 'area', 'uniform-environment'], no_clamping=True,
                no_media_textures_splats_denoising_temporal_reuse=True)
STREAMS = dict(master_seed=20261007, replicates=list(range(8)), reference_replicate=0,
               names=['allocation', 'production', 'reference-a', 'reference-b', 'timing-order'],
               derivation='first eight big-endian SHA-256 bytes of UTF-8 tc-r1-v1|20261007|scene_id|frame_id|replicate|stream',
               sample_mapping='Track A production interface; seed derivation alone does not freeze sampler dimensions')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), label + ' fields')


def number(value, lower=None, upper=None):
    require(type(value) in (int, float) and math.isfinite(value), 'finite numeric value')
    require(lower is None or value >= lower, 'numeric lower bound')
    require(upper is None or value <= upper, 'numeric upper bound')


def vector(value, length=3, lower=None, upper=None):
    require(isinstance(value, list) and len(value) == length, 'vector shape')
    for item in value:
        number(item, lower, upper)


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def difference(a, b):
    return [x-y for x, y in zip(a, b)]


def nonzero(value):
    return any(v != 0 for v in value)


def shape(value):
    require(isinstance(value, dict), 'shape object')
    kind = value.get('type')
    if kind == 'sphere':
        keys(value, ['type', 'center', 'radius'], 'sphere')
        vector(value['center'])
        number(value['radius'])
        require(value['radius'] > 0, 'sphere radius')
    elif kind == 'trianglemesh':
        keys(value, ['type', 'vertices', 'indices'], 'trianglemesh')
        points, indices = value['vertices'], value['indices']
        require(isinstance(points, list) and len(points) >= 3, 'mesh vertices')
        for point in points:
            vector(point)
        require(isinstance(indices, list) and len(indices) >= 3 and len(indices) % 3 == 0,
                'triangle indices shape')
        require(all(type(i) is int and 0 <= i < len(points) for i in indices), 'triangle indices')
        for offset in range(0, len(indices), 3):
            a, b, c = [points[i] for i in indices[offset:offset+3]]
            require(nonzero(cross(difference(b, a), difference(c, a))), 'degenerate triangle')
    else:
        raise ValueError('out-of-envelope geometry: ' + str(kind))


def validate_definition(value):
    keys(value, ['camera', 'materials', 'lights', 'objects'], 'scene definition')
    camera = value['camera']
    keys(camera, ['position', 'target', 'up', 'fov'], 'camera')
    for name in ['position', 'target', 'up']:
        vector(camera[name])
    number(camera['fov'])
    require(0 < camera['fov'] < 180, 'perspective field of view')
    direction = difference(camera['target'], camera['position'])
    require(nonzero(cross(direction, camera['up'])), 'camera look/up degeneracy')
    materials = value['materials']
    require(isinstance(materials, dict) and materials, 'material definitions')
    for name, material in materials.items():
        require(isinstance(name, str) and name.isascii() and name.replace('-', '').isalnum(),
                'material name')
        kind = material.get('type') if isinstance(material, dict) else None
        if kind == 'diffuse':
            keys(material, ['type', 'reflectance'], 'diffuse')
            vector(material['reflectance'], lower=0, upper=1)
        elif kind == 'conductor':
            keys(material, ['type', 'reflectance', 'roughness'], 'conductor')
            vector(material['reflectance'], lower=0, upper=1)
            number(material['roughness'], 0, 1)
        elif kind == 'dielectric':
            keys(material, ['type', 'eta', 'roughness'], 'dielectric')
            number(material['eta'])
            require(material['eta'] > 0, 'dielectric eta')
            number(material['roughness'], 0, 1)
        else:
            raise ValueError('out-of-envelope material: ' + str(kind))
    lights = value['lights']
    require(isinstance(lights, list) and lights, 'light definitions')
    for light in lights:
        require(isinstance(light, dict), 'light object')
        kind = light.get('type')
        if kind == 'point':
            keys(light, ['type', 'position', 'intensity'], 'point light')
            vector(light['position'])
            vector(light['intensity'], lower=0)
        elif kind == 'uniform-environment':
            keys(light, ['type', 'radiance'], 'uniform environment')
            vector(light['radiance'], lower=0)
        elif kind == 'area':
            keys(light, ['type', 'radiance', 'shape', 'two_sided'], 'area light')
            vector(light['radiance'], lower=0)
            require(type(light['two_sided']) is bool, 'area light sidedness')
            shape(light['shape'])
        else:
            raise ValueError('out-of-envelope light: ' + str(kind))
    objects = value['objects']
    require(isinstance(objects, list) and objects, 'object definitions')
    for item in objects:
        keys(item, ['material', 'shape'], 'object')
        require(item['material'] in materials, 'unbound material')
        shape(item['shape'])


def load(path):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, 'duplicate JSON field: ' + name)
            result[name] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def canonical(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bracket(values):
    return '[' + ' '.join(format(v, '.12g') for v in values) + ']'


def emit_shape(value):
    if value['type'] == 'sphere':
        return ['Translate ' + ' '.join(format(v, '.12g') for v in value['center']),
                'Shape "sphere" "float radius" ' + bracket([value['radius']])]
    return ['Shape "trianglemesh" "point3 P" ' + bracket([n for p in value['vertices'] for n in p]) +
            ' "integer indices" ' + bracket(value['indices'])]


def emit_material(material):
    kind = material['type']
    line = 'Material "' + kind + '"'
    if kind in ('diffuse', 'conductor'):
        line += ' "rgb reflectance" ' + bracket(material['reflectance'])
    if kind == 'dielectric':
        line += ' "float eta" ' + bracket([material['eta']])
    if kind in ('conductor', 'dielectric'):
        line += ' "float roughness" ' + bracket([material['roughness']])
        line += ' "bool remaproughness" [true]'
    return line


def serialize(value):
    validate_definition(value)
    c = value['camera']
    lines = ['# Original TC-R1 procedural asset; SPDX-License-Identifier: MIT OR Apache-2.0',
             '# No policy outcomes used in authoring; no temporal reuse or motion blur.',
             'LookAt ' + ' '.join(format(v, '.12g') for key in ['position', 'target', 'up'] for v in c[key]),
             'Camera "perspective" "float fov" ' + bracket([c['fov']]) + ' "float lensradius" [0]',
             'Film "rgb" "integer xresolution" [256] "integer yresolution" [256]',
             '# Nominal startup 16 spp; Track A must bind execution sample-index mapping separately.',
             'Sampler "independent" "integer pixelsamples" [16]',
             'Integrator "path" "integer maxdepth" [8] "bool regularize" [false]',
             'PixelFilter "box" "float xradius" [0.5] "float yradius" [0.5]', 'WorldBegin']
    for light in value['lights']:
        kind = light['type']
        if kind == 'point':
            lines.append('LightSource "point" "point3 from" ' + bracket(light['position']) +
                         ' "rgb I" ' + bracket(light['intensity']))
        elif kind == 'uniform-environment':
            lines.append('LightSource "infinite" "rgb L" ' + bracket(light['radiance']))
        else:
            lines.extend(['AttributeBegin', 'AreaLightSource "diffuse" "rgb L" ' +
                          bracket(light['radiance']) + ' "bool twosided" [' +
                          str(light['two_sided']).lower() + ']',
                          'Material "diffuse" "rgb reflectance" [0 0 0]'])
            lines.extend(emit_shape(light['shape']))
            lines.append('AttributeEnd')
    for item in value['objects']:
        lines.extend(['AttributeBegin', emit_material(value['materials'][item['material']])])
        lines.extend(emit_shape(item['shape']))
        lines.append('AttributeEnd')
    return ('\n'.join(lines) + '\n').encode('utf-8')


def source_scenes(root):
    schema = load(root / DIRECTORY / 'schema.json')
    require(isinstance(schema, dict) and schema.get('schema_version') == 1, 'schema version')
    identities = [prefix + '-' + variant for prefix in FAMILIES for variant in ['01', '02']]
    require(schema.get('scene_ids') == identities and schema.get('envelope') == ENVELOPE and
            schema.get('streams') == STREAMS and schema.get('families') == list(FAMILIES.values()) and
            schema.get('resolution') == [256, 256] and schema.get('units') == 'metres' and
            schema.get('frames') == [dict(frame_id='f'+str(i), time=t) for i,t in enumerate(TIMES)],
            'frozen schema identities/envelope')
    scenes = load(root / DIRECTORY / 'specifications.json')
    require(isinstance(scenes, list) and all(isinstance(s, dict) for s in scenes) and
            [s.get('scene_id') for s in scenes] == identities,
            'exact ordered scene identities')
    for scene in scenes:
        keys(scene, ['scene_id', 'family', 'variant', 'rationale', 'frames'], 'scene specification')
        prefix, variant = scene['scene_id'].split('-')
        require(scene['family'] == FAMILIES[prefix] and type(scene['variant']) is int and
                scene['variant'] == int(variant), 'family and variant')
        require(isinstance(scene['rationale'], str) and scene['rationale'].strip(), 'family rationale')
        frames = scene['frames']
        require(isinstance(frames, list) and len(frames) == 3, 'three frames per scene')
        for index, frame in enumerate(frames):
            keys(frame, ['frame_id', 'time', 'definition'], 'frame specification')
            number(frame['time'])
            require(frame['frame_id'] == 'f' + str(index) and frame['time'] == TIMES[index],
                    'fixed frame identity/time')
            validate_definition(frame['definition'])
        definitions = [canonical(f['definition']) for f in frames]
        require(len(set(definitions)) == (3 if prefix == 'motion' else 1),
                'static repetition or distinct motion definitions')
    return schema, scenes


def expected(root=ROOT):
    schema, scenes = source_scenes(root)
    input_paths = [DIRECTORY / 'schema.json', DIRECTORY / 'specifications.json',
                   Path('experiments/tc-r1/corpus.py'), Path('LICENSE-MIT'), Path('LICENSE-APACHE')]
    require(all((root / p).resolve().is_relative_to(root.resolve()) for p in input_paths),
            'input resolved path escape')
    inputs = {p.as_posix(): digest((root / p).read_bytes()) for p in input_paths}
    files = {}
    entries = []
    for scene in scenes:
        frames = []
        for frame in scene['frames']:
            path = (DIRECTORY / 'scenes' / scene['scene_id'] / (frame['frame_id'] + '.pbrt')).as_posix()
            data = serialize(frame['definition'])
            files[path] = data
            frames.append(dict(frame_id=frame['frame_id'], time=frame['time'], path=path,
                               sha256=digest(data), definition=frame['definition']))
        entries.append({k: scene[k] for k in ['scene_id', 'family', 'variant', 'rationale']} |
                       dict(specification='research/tc-r1/corpus/specifications.json#' + scene['scene_id'],
                            frames=frames))
    manifest = dict(schema_version=1, status='assets-authored; not execution-preregistered',
                    pbrt_commit=PBRT_COMMIT, envelope=schema['envelope'], units='metres',
                    resolution=[256, 256], frame_times=TIMES, streams=schema['streams'],
                    license=dict(spdx='MIT OR Apache-2.0', provenance='Original procedural definitions authored for this repository',
                                 external_assets=False, files=['LICENSE-MIT', 'LICENSE-APACHE']),
                    inputs=inputs, scenes=entries)
    require(set(manifest) == set(schema['manifest_keys']), 'manifest fields')
    return manifest, files


def verify(root=ROOT):
    path = root / DIRECTORY / 'manifest.json'
    require(not path.is_symlink() and path.is_file() and
            path.resolve().is_relative_to(root.resolve()), 'manifest must be an in-root regular file')
    manifest, files = expected(root)
    actual = load(path)
    require(actual == manifest, 'manifest/source/hash mismatch')
    require(path.read_bytes() == canonical(manifest), 'noncanonical manifest bytes')
    scene_root = root / DIRECTORY / 'scenes'
    require(all(not p.is_symlink() for p in [root / 'research', root / 'research/tc-r1',
                                            root / DIRECTORY, scene_root]), 'symlinked scene parent')
    entries = list(scene_root.rglob('*'))
    require(all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in entries),
            'symlinked or non-regular scene entry')
    present = {p.relative_to(root).as_posix() for p in entries if p.is_file()}
    require(present == set(files), 'missing or additional scene assets')
    for name, data in files.items():
        pure = PurePosixPath(name)
        require(not pure.is_absolute() and '..' not in pure.parts, 'asset path traversal')
        asset = root / name
        require(asset.resolve().is_relative_to(root.resolve()), 'asset resolved path escape')
        require(asset.read_bytes() == data, 'asset bytes differ: ' + name)
    return dict(scenes=len(manifest['scenes']), frames=len(files),
                manifest_sha256=digest(path.read_bytes()), rendering_performed=False)


def write(root=ROOT):
    manifest, files = expected(root)
    paths = [root / name for name in files] + [root / DIRECTORY / 'manifest.json']
    require(all(path.resolve().is_relative_to(root.resolve()) for path in paths),
            'output resolved path escape')
    require(not any(path.exists() for path in paths),
            'assets already authored; preserve them and use an explicit reviewed correction/amendment')
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / DIRECTORY / 'manifest.json').write_bytes(canonical(manifest))
    return verify(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='First authoring only; refuses existing assets')
    args = parser.parse_args()
    print(json.dumps(write() if args.write else verify(), indent=2))
